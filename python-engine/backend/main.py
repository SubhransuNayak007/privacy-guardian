import base64
import time
import numpy as np
import cv2
import psutil
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from detector.image_enhancement import strip_exif, check_image_quality, enhance_image
from detector.yolo_engine import run_yolo_tile, run_yolo_batch
from detector.box_fusion import expand_and_merge
from ocr.ocr_router import run_targeted_ocr
from pii.presidio_engine import analyze_text
from pii.regex_engine import detect_regex
from pii.risk_score import calculate_risk_score
from vlm.vlm_router import call_vlm
from segmentation.blur import apply_gaussian_blur

app = FastAPI(title="Privacy Guardian v2 Production Architecture")

# --- PYDANTIC MODELS ---
class ScanRequest(BaseModel):
    imageBase64: str

class ScanResponse(BaseModel):
    job_id: str
    status: str
    message: str

class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

class AIBox(BaseModel):
    type: str
    confidence: float
    bbox: BoundingBox
    text: str = ""
    redacted: bool = False

# Simple in-memory results store for the async queue pattern
job_results = {}

def process_image_task(job_id: str, b64_str: str):
    t0 = time.time()
    try:
        if b64_str.startswith("data:image"):
            parts = b64_str.split(",")
            if len(parts) > 1:
                b64_str = parts[1]
            
        img_data = base64.b64decode(b64_str)
        img_data = strip_exif(img_data)
        
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Invalid image")
            
        H, W = img.shape[:2]
        
        # 1. Quality Check
        if not check_image_quality(img):
            job_results[job_id] = {"status": "error", "message": "Image too blurry or dark."}
            return
            
        # 2. Enhancement
        img_enh = enhance_image(img)
        
        # 3. Tiling
        overlap = 128
        mid_y, mid_x = H // 2, W // 2
        tiles = []
        tiles.append((img_enh[0:min(mid_y+overlap, H), 0:min(mid_x+overlap, W)], 0, 0, min(mid_x+overlap, W), min(mid_y+overlap, H)))
        tiles.append((img_enh[0:min(mid_y+overlap, H), max(0, mid_x-overlap):W], max(0, mid_x-overlap), 0, W, min(mid_y+overlap, H)))
        tiles.append((img_enh[max(0, mid_y-overlap):H, 0:min(mid_x+overlap, W)], 0, max(0, mid_y-overlap), min(mid_x+overlap, W), H))
        tiles.append((img_enh[max(0, mid_y-overlap):H, max(0, mid_x-overlap):W], max(0, mid_x-overlap), max(0, mid_y-overlap), W, H))
        
        all_raw = []
        # Batched processing of 4 tiles
        patches = [t[0] for t in tiles]
        batch_dets_list = run_yolo_batch(patches)
        for t, patch_dets in zip(tiles, batch_dets_list):
            for d in patch_dets:
                d["box"][0] += t[1]
                d["box"][1] += t[2]
                d["box"][2] += t[1]
                d["box"][3] += t[2]
                all_raw.append(d)
                
        # 4. Box Fusion
        merged_boxes = expand_and_merge(all_raw, W, H, overlap=overlap, expand_px=8)
        
        # 5. Full Image OCR (Targeted OCR missed text if YOLO failed to detect document)
        ocr_lines = run_targeted_ocr(img_enh, merged_boxes)
        
        # 6. PII & Risk
        pii_boxes = []
        for box, txt, conf in ocr_lines:
            regex_label = detect_regex(txt)
            presidio_label = analyze_text(txt)
            final_label = regex_label if regex_label else (presidio_label if presidio_label else None)
            
            if final_label:
                pii_boxes.append({
                    "box": [min([p[0] for p in box])/W, min([p[1] for p in box])/H, max([p[0] for p in box])/W, max([p[1] for p in box])/H],
                    "label": final_label,
                    "score": conf,
                    "text": txt
                })
                
        final_dets = merged_boxes + pii_boxes
        risk = calculate_risk_score(final_dets)
        
        # 7. VLM Conditional
        for d in final_dets:
            if d["label"].lower() in ["document", "invoice"] and d["score"] < 0.8:
                # crop and call
                call_vlm(img, d["label"], d["score"])
                
        # 8. Blur (We'll just blur all PII and sensitive YOLO targets for now)
        sensitive_labels = ["pii_text", "face", "nsfw", "license_plate", "aadhaar", "pan", "dob", "name", "email", "phone", "address", "bank_account", "credit_card", "password"]
        blur_boxes = [d["box"] for d in final_dets if d["label"].lower() in sensitive_labels]
        img_blurred = apply_gaussian_blur(img, blur_boxes)
        
        _, buffer = cv2.imencode('.jpg', img_blurred)
        b64_out = base64.b64encode(buffer).decode('utf-8')
        
        process_time = int((time.time() - t0) * 1000)
        
        # Map back to old output format for frontend compatibility
        detections = []
        for fd in final_dets:
            bx = fd["box"]
            detections.append(AIBox(
                type=fd["label"],
                confidence=float(fd["score"]) * 100.0,
                bbox=BoundingBox(x0=bx[0]*100, y0=bx[1]*100, x1=bx[2]*100, y1=bx[3]*100),
                text=fd.get("text", ""),
                redacted=(fd["label"].lower() in sensitive_labels)
            ))

        job_results[job_id] = {
            "status": "completed",
            "image": b64_out,
            "detections": [d.dict() for d in detections],
            "risk_score": risk,
            "processing_time": process_time
        }
    except Exception as e:
        job_results[job_id] = {"status": "error", "message": str(e)}

@app.post("/scan", response_model=ScanResponse)
async def scan_endpoint(req: ScanRequest, background_tasks: BackgroundTasks):
    job_id = "job_" + str(int(time.time() * 1000))
    job_results[job_id] = {"status": "processing"}
    
    # 9. Async Queue
    background_tasks.add_task(process_image_task, job_id, req.imageBase64)
    
    return ScanResponse(job_id=job_id, status="processing", message="Image added to queue.")

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    if job_id not in job_results:
        return {
            "id": job_id,
            "status": "error",
            "message": "Job not found",
            "result": {
                "riskLevel": "low",
                "detections": [],
                "image": ""
            }
        }
        
    res = job_results[job_id]
    status = res.get("status", "error")
    
    if status == "processing":
        return {
            "id": job_id,
            "status": "processing",
            "message": res.get("message", "Processing"),
            "result": None
        }
    elif status == "completed":
        return {
            "id": job_id,
            "status": "completed",
            "message": "Success",
            "result": {
                "riskLevel": str(res.get("risk_score", "low")).lower(),
                "detections": res.get("detections", []),
                "image": res.get("image", ""),
                "processingTime": res.get("processing_time", 0)
            }
        }
    else:
        return {
            "id": job_id,
            "status": "error",
            "message": res.get("message", "Unknown error"),
            "result": {
                "riskLevel": "low",
                "detections": [],
                "image": ""
            }
        }
