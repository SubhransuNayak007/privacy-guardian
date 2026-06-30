import requests, base64, cv2

img = cv2.imread('test_image.jpg')
_, buf = cv2.imencode('.jpg', img)
b64 = 'data:image/jpeg;base64,' + base64.b64encode(buf).decode()

r = requests.post('http://127.0.0.1:8000/scan', json={'imageBase64': b64}, timeout=90)
data = r.json()
print('Status:', r.status_code)
print('Detections:', len(data.get('detections', [])))
print('Privacy Score:', data.get('privacyScore'))
print('Diagnostics:', data.get('diagnostics'))
for d in data.get('detections', [])[:15]:
    label = d['label']
    text = d['text'][:50]
    conf = d['confidence']
    dtype = d['type']
    print(f"  - [{dtype}] {label}: {text} (conf={conf:.0f}%)")
