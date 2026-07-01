import os
import sys
import time
import base64
import numpy as np
import cv2
import json
from unittest.mock import patch

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app import app
from pipeline import execute_pipeline
from models.manager import ModelManager

results = {}

def report(name, status, msg=""):
    results[name] = {"status": status, "msg": msg}
    print(f"[{status}] {name} - {msg}")

def create_synthetic_image_b64():
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    img[:] = (255, 255, 255)
    cv2.putText(img, "TEST", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    _, buf = cv2.imencode('.jpg', img)
    return base64.b64encode(buf).decode('utf-8')

# Patch ModelManager to return mocks to avoid slow loading
def get_mocked_manager():
    m = ModelManager()
    m._yolo = "unavailable"
    m._paddle = "unavailable"
    m._presidio = "unavailable"
    m._vlm = "unavailable"
    return m

@patch("pipeline.ModelManager", return_value=get_mocked_manager())
def run_all_tests(mock_manager):
    # Task 1: Confidence Fusion
    b64 = create_synthetic_image_b64()
    b64_out, dets, ptime = execute_pipeline(b64)
    if any('risk_score' in d for d in dets):
        report("Confidence Fusion", "PASS", "Risk score found.")
    else:
        report("Confidence Fusion", "FAIL", "No risk_score in detections. Logic missing.")

    # Task 2: Tier-2 Routing
    with patch("services.detector.DetectorService.run_detection") as mock_detect, \
         patch("services.vlm.VLMService.call") as mock_vlm_call:
        mock_detect.return_value = [{"box": [0.1, 0.1, 0.5, 0.5], "score": 0.5, "label": "document"}]
        mock_vlm_call.return_value = {"extracted_text": "secret plan", "sensitive_regions": []}
        execute_pipeline(b64)
        if mock_vlm_call.called:
            report("Tier-2 Routing", "PASS", "VLM was triggered for low confidence document.")
        else:
            report("Tier-2 Routing", "FAIL", "VLM was not triggered.")

    # Task 3: Tier-3 FastSAM
    with patch("services.detector.DetectorService.run_detection") as mock_detect:
        mock_detect.return_value = [{"box": [0.1, 0.1, 0.5, 0.5], "score": 0.9, "label": "tattoo"}]
        b64_out, dets, ptime = execute_pipeline(b64)
        if any('mask' in d for d in dets):
            report("Tier-3 FastSAM", "PASS", "Mask found in detection.")
        else:
            report("Tier-3 FastSAM", "FAIL", "No mask-based FastSAM logic found for tattoo.")

    # Task 4: Redaction Quality
    from services.blur import BlurService
    bs = BlurService()
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    img[:] = (255, 255, 255)
    cv2.putText(img, "TXT", (25, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    out = bs.apply_gaussian_blur(img, [[0.2, 0.2, 0.8, 0.8]])
    diff = np.sum(np.abs(img[20:80, 20:80].astype(int) - out[20:80, 20:80].astype(int)))
    bg_diff = np.sum(np.abs(img[0:19, 0:100].astype(int) - out[0:19, 0:100].astype(int)))
    if diff > 0 and bg_diff == 0:
        report("Redaction Quality", "PASS", "Gaussian blur covers box and doesn't leak to background.")
    else:
        report("Redaction Quality", "FAIL", "Blur leaked or didn't apply.")

    # With TestClient to test endpoints
    with TestClient(app) as client:
        # Task 5: Async Queue
        t0 = time.time()
        resp = client.post("/scan", json={"imageBase64": b64})
        t1 = time.time()
        dur = (t1 - t0) * 1000
        if resp.status_code == 200 and dur < 200:
            report("Async Queue", "PASS", f"Endpoint returned in {dur:.2f}ms with status {resp.json().get('status')}")
        else:
            report("Async Queue", "FAIL", f"Took {dur:.2f}ms or failed.")

        # Task 6: Error Handling
        resp = client.post("/scan", json={"imageBase64": "corrupt_data_not_base64"})
        job_id = resp.json().get("job_id")
        if job_id:
            time.sleep(0.5)
            res = client.get(f"/result/{job_id}")
            if res.json().get("status") == "error":
                report("Error Handling", "PASS", "Handled corrupt image gracefully.")
            else:
                report("Error Handling", "FAIL", f"Failed to handle corrupt image. Status: {res.json().get('status')}")
        else:
             report("Error Handling", "FAIL", "No job_id returned for corrupt image.")

        # Task 7: Security (Data Retention)
        import glob
        files_before = set(glob.glob("**/*", recursive=True))
        execute_pipeline(b64)
        files_after = set(glob.glob("**/*", recursive=True))
        diff_files = files_after - files_before
        diff_files = [f for f in diff_files if "__pycache__" not in f and not f.endswith(".pyc")]
        if len(diff_files) == 0:
            report("Security (Data Retention)", "PASS", "No temp files left on disk.")
        else:
            report("Security (Data Retention)", "FAIL", f"Files leaked: {diff_files}")

        # Task 8: Performance (10 requests)
        t0 = time.time()
        jobs = []
        for _ in range(10): 
            r = client.post("/scan", json={"imageBase64": b64})
            jobs.append(r.json().get("job_id"))
        
        done = 0
        while done < 10 and (time.time() - t0) < 10:
            done = 0
            for j in jobs:
                if not j: continue
                res = client.get(f"/result/{j}")
                if res.status_code == 200 and res.json().get("status") in ["completed", "error"]:
                    done += 1
            time.sleep(0.5)
        
        t_total = time.time() - t0
        if done == 10 and (t_total/10) < 2.0:
            report("Performance", "PASS", f"10 requests in {t_total:.2f}s (avg {t_total/10:.2f}s)")
        else:
            report("Performance", "FAIL", f"Completed {done}/10 in {t_total:.2f}s (avg > 2s or timeout).")

        # Task 9: Logging
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pipeline.py"), "r") as f:
            content = f.read()
        if "logging.info" in content or "logger." in content:
            report("Logging", "PASS", "Structured logging found.")
        else:
            report("Logging", "FAIL", "No standard logging found in pipeline.")

if __name__ == "__main__":
    run_all_tests()
    with open("qa_results.json", "w") as f:
        json.dump(results, f, indent=2)
