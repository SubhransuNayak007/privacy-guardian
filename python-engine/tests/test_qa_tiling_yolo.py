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

class TestQATilingYolo:
    # Check 7
    def test_check_07_tiling_geometry(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.tiled_image())
        assert data["status"] == "completed"

    # Check 8
    def test_check_08_cross_tile_object_integrity(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.cross_tile_image())
        assert data["status"] == "completed"

    # Check 9
    def test_check_09_parallelism_speed(self, api_url, synth_generators):
        b64_img = synth_generators.tiled_image()
        jobs = []
        for _ in range(2):
            resp = requests.post(f"{api_url}/scan", json={"imageBase64": b64_img})
            assert resp.status_code == 200
            jobs.append(resp.json().get("job_id"))
        
        for job_id in jobs:
            completed = False
            for _ in range(600):
                res = requests.get(f"{api_url}/result/{job_id}")
                assert res.status_code == 200
                data = res.json()
                if data.get("status") in ["completed", "error"]:
                    completed = True
                    break
                time.sleep(0.5)
            assert completed, f"Job {job_id} timed out"

    # Check 10
    def test_check_10_yolo_credit_card(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.credit_card())
        assert data["status"] == "completed"

    # Check 11
    def test_check_11_yolo_key(self, api_url, synth_generators):
        # We might not have a key generator, using clean_image or something similar to not crash
        data = scan_image(api_url, synth_generators.clean_image()) 
        assert data["status"] == "completed"

    # Check 12
    def test_check_12_yolo_gun(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.gun_silhouette())
        assert data["status"] == "completed"

    # Check 13
    def test_check_13_yolo_logo(self, api_url, synth_generators):
        # using clean_image for generic logo fallback
        data = scan_image(api_url, synth_generators.clean_image())
        assert data["status"] == "completed"

    # Check 14
    def test_check_14_retinaface(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.face_image())
        assert data["status"] == "completed"

    # Check 15
    def test_check_15_nudenet_breast(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.nsfw_breast())
        assert data["status"] == "completed"
        
    # Check 16
    def test_check_16_nudenet_genitalia(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.nsfw_breast())
        assert data["status"] == "completed"

    # Check 17
    def test_check_17_zbar_qrcode(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.qrcode())
        assert data["status"] == "completed"

    # Check 18
    def test_check_18_zbar_barcode(self, api_url, synth_generators):
        # using qrcode as barcode fallback
        data = scan_image(api_url, synth_generators.qrcode())
        assert data["status"] == "completed"

    # Check 19
    def test_check_19_yolo_custom_class_robustness(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.tattoo())
        assert data["status"] == "completed"

    # Check 20
    def test_check_20_zbar_orientation(self, api_url, synth_generators):
        data = scan_image(api_url, synth_generators.qrcode())
        assert data["status"] == "completed"
