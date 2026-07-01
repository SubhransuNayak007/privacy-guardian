from typing import List, Dict, Any
import cv2
import os

_yolo_model = None
_face_cascade = None
_plate_cascade = None

def get_yolo():
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            import os
            model_path = "yolo11s_custom.pt" if os.path.exists("yolo11s_custom.pt") else "yolov8n.pt"
            _yolo_model = YOLO(model_path)
        except Exception:
            _yolo_model = "unavailable"
    return _yolo_model

def get_cascades():
    global _face_cascade, _plate_cascade
    if _face_cascade is None:
        try:
            face_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
            if os.path.exists(face_path):
                _face_cascade = cv2.CascadeClassifier(face_path)
            plate_path = os.path.join(cv2.data.haarcascades, 'haarcascade_russian_plate_number.xml')
            if os.path.exists(plate_path):
                _plate_cascade = cv2.CascadeClassifier(plate_path)
        except Exception as e:
            print(f"Error loading cascades: {e}")
    return _face_cascade, _plate_cascade

def run_yolo_tile(patch) -> List[Dict[str, Any]]:
    yolo = get_yolo()
    dets = []
    if yolo != "unavailable" and yolo is not None:
        res = yolo.predict(patch, verbose=False)[0]
        for box in res.boxes:
            conf = float(box.conf[0])
            if conf > 0.3:
                name = res.names[int(box.cls[0])]
                x1, y1, x2, y2 = map(float, box.xyxy[0])
                dets.append({"box": [x1, y1, x2, y2], "score": conf, "label": name})
    return dets

def run_yolo_batch(patches) -> List[List[Dict[str, Any]]]:
    yolo = get_yolo()
    face_casc, plate_casc = get_cascades()
    batch_dets = []
    if not patches:
        return []
        
    if yolo != "unavailable" and yolo is not None:
        results = yolo.predict(patches, verbose=False)
        for i, res in enumerate(results):
            dets = []
            for box in res.boxes:
                conf = float(box.conf[0])
                if conf > 0.3:
                    name = res.names[int(box.cls[0])]
                    x1, y1, x2, y2 = map(float, box.xyxy[0])
                    dets.append({"box": [x1, y1, x2, y2], "score": conf, "label": name})
                    
            # Run Haar Cascades
            patch = patches[i]
            if patch is not None and patch.size > 0:
                try:
                    gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
                    if face_casc is not None and not face_casc.empty():
                        faces = face_casc.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(20, 20))
                        for (x, y, w, h) in faces:
                            dets.append({
                                "box": [float(x), float(y), float(x+w), float(y+h)],
                                "score": 0.85,
                                "label": "face"
                            })
                    if plate_casc is not None and not plate_casc.empty():
                        plates = plate_casc.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 10))
                        for (x, y, w, h) in plates:
                            dets.append({
                                "box": [float(x), float(y), float(x+w), float(y+h)],
                                "score": 0.85,
                                "label": "license_plate"
                            })
                except Exception:
                    pass
            batch_dets.append(dets)
    else:
        batch_dets = [[] for _ in patches]
    return batch_dets


