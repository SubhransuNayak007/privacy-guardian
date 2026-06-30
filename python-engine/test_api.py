import requests

def test_scan_api():
    url = "http://localhost:8000/scan"
    
    # 1x1 transparent PNG base64 encoded
    dummy_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    
    payload = {
        "imageBase64": dummy_image_b64
    }
    
    try:
        print(f"Sending POST request to {url}...")
        response = requests.post(url, json=payload)
        
        # Assert status code is 200
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}. Response: {response.text}"
        
        # Parse JSON response
        data = response.json()
        
        # Assert keys are present
        assert "detections" in data, "'detections' key missing from response"
        assert "words" in data, "'words' key missing from response"
        
        print("Test passed successfully!")
        print(f"Response: {data}")
        
    except requests.exceptions.ConnectionError:
        print(f"Error: Failed to connect to {url}. Ensure the server is running.")
    except AssertionError as e:
        print(f"Test failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_scan_api()
