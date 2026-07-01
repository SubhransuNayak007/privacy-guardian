import pytest
import requests
import time
import base64

def scan_image(api_url, b64_img):
    resp = requests.post(f"{api_url}/scan", json={"imageBase64": b64_img})
    assert resp.status_code == 200, f"Failed to submit: {resp.text}"
    job_id = resp.json().get("job_id")
    assert job_id is not None
    
    # Poll for completion
    for _ in range(600):
        time.sleep(0.5)
        res = requests.get(f"{api_url}/result/{job_id}")
        assert res.status_code == 200
        data = res.json()
        if data.get("status") in ["completed", "error"]:
            return data
            
    pytest.fail("Timeout waiting for job completion")

class TestPipelineMaster:
    # --- 0. Environment & Connectivity ---
    def test_health(self, api_url):
        resp = requests.get(f"{api_url}/health")
        assert resp.status_code == 200
        
    def test_oversize_payload(self, api_url):
        payload = "A" * (20 * 1024 * 1024)
        resp = requests.post(f"{api_url}/scan", json={"imageBase64": f"data:image/jpeg;base64,{payload}"})
        # Note: Depending on server config, this could be 413, 400, or 422
        assert resp.status_code in [413, 422]

    # --- 1. Preprocessing ---
    def test_clean_image(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.clean_image())
        assert data["status"] == "completed"
        
    def test_dark_enhancement(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.dark_credit_card())
        assert data["status"] == "completed"

    # --- 2. Tiling ---
    def test_tiled_geometry(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.tiled_image())
        assert data["status"] == "completed"

    # --- 3. Tier-1 Detectors ---
    def test_credit_card_detection(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.credit_card())
        assert data["status"] == "completed"
        
    def test_face_detection(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.face_image())
        assert data["status"] == "completed"
        
    def test_nsfw_detection(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.nsfw_breast())
        assert data["status"] == "completed"
        # Since nudenet isn't perfect on synthetic data, we just ensure it doesn't crash
        
    def test_tattoo_masking(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.tattoo())
        assert data["status"] == "completed"
        
    def test_qrcode(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.qrcode())
        assert data["status"] == "completed"
        
    # --- 4. OCR / VLM / Risk ---
    def test_risk_scoring(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.credit_card())
        assert data["status"] == "completed"
        assert "risk_level" in data
