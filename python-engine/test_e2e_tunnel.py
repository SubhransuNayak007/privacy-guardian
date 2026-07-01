import requests
import time
import sys

import base64
import os

TUNNEL_URL = "https://sweet-shirts-sneeze.loca.lt"

with open("test_image.jpg", "rb") as f:
    dummy_b64 = base64.b64encode(f.read()).decode('utf-8')


def test_tunnel():
    print(f"Testing tunnel at {TUNNEL_URL}...")
    
    headers = {
        "Bypass-Tunnel-Reminder": "true",
        "Content-Type": "application/json"
    }
    
    payload = {
        "imageBase64": dummy_b64
    }
    
    print("1. Sending POST /scan")
    try:
        post_response = requests.post(f"{TUNNEL_URL}/scan", json=payload, headers=headers)
    except Exception as e:
        print(f"POST /scan failed with exception: {e}")
        return False
        
    if post_response.status_code == 503:
        print("FAIL: POST /scan returned 503 Tunnel Unavailable")
        return False
        
    if post_response.status_code != 200:
        print(f"FAIL: POST /scan returned {post_response.status_code}: {post_response.text}")
        return False
        
    data = post_response.json()
    job_id = data.get("job_id")
    if not job_id:
        print("FAIL: No job_id returned in response")
        return False
        
    print(f"Got job_id: {job_id}")
    print("2. Polling GET /result/{job_id}")
    
    max_retries = 30
    for i in range(max_retries):
        try:
            get_response = requests.get(f"{TUNNEL_URL}/result/{job_id}", headers=headers)
        except Exception as e:
            print(f"GET /result failed with exception: {e}")
            return False
            
        if get_response.status_code == 503:
            print("FAIL: GET /result returned 503 Tunnel Unavailable")
            return False
            
        if get_response.status_code != 200:
            print(f"FAIL: GET /result returned {get_response.status_code}: {get_response.text}")
            return False
            
        res_data = get_response.json()
        status = res_data.get("status")
        
        print(f"Poll {i+1}: status = {status}")
        
        if status == "completed":
            print("Job completed!")
            
            # Validate schema
            expected_keys = ["id", "status", "message", "result"]
            for key in expected_keys:
                if key not in res_data:
                    print(f"FAIL: Missing key '{key}' in response")
                    return False
                    
            result_obj = res_data["result"]
            if not isinstance(result_obj, dict):
                print("FAIL: 'result' is not a dictionary")
                return False
                
            expected_result_keys = ["riskLevel", "detections"]
            for key in expected_result_keys:
                if key not in result_obj:
                    print(f"FAIL: Missing key '{key}' in result object")
                    return False
            
            if not isinstance(result_obj["detections"], list):
                print("FAIL: 'detections' is not a list")
                return False
                
            if not isinstance(result_obj["riskLevel"], str):
                print("FAIL: 'riskLevel' is not a string")
                return False

                    
            print("SUCCESS! Schema is valid and no 503s were encountered.")
            return True
            
        elif status == "error":
            print(f"FAIL: Job failed with error: {res_data.get('message')}")
            return False
            
        time.sleep(2)
        
    print("FAIL: Polling timed out")
    return False

if __name__ == "__main__":
    success = test_tunnel()
    if not success:
        sys.exit(1)
    sys.exit(0)
