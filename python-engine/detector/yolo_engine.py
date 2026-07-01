from typing import List, Dict, Any
import cv2
import os
import numpy as np

_yolo_model = None
_face_app = None
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

def get_models():
    global _face_app, _plate_cascade
    if _face_app is None:
        try:
            from insightface.app import FaceAnalysis
            _face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
            _face_app.prepare(ctx_id=0, det_size=(640, 640))
        except Exception as e:
            print(f"Error loading insightface: {e}")
            _face_app = "unavailable"
            
    if _plate_cascade is None:
        try:
            plate_path = os.path.join(cv2.data.haarcascades, 'haarcascade_russian_plate_number.xml')
            if os.path.exists(plate_path):
                _plate_cascade = cv2.CascadeClassifier(plate_path)
        except Exception as e:
            print(f"Error loading plate cascade: {e}")
            _plate_cascade = "unavailable"
            
    return _face_app, _plate_cascade

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
    face_app, plate_casc = get_models()
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
                    
            # Run Face & Plate Detection
            patch = patches[i]
            if patch is not None and patch.size > 0:
                try:
                    if face_app is not None and face_app != "unavailable":
                        faces = face_app.get(patch)
                        for face in faces:
                            fx1, fy1, fx2, fy2 = face.bbox
                            score = float(face.det_score)
                            if score > 0.3:
                                dets.append({
                                    "box": [float(fx1), float(fy1), float(fx2), float(fy2)],
                                    "score": score,
                                    "label": "face"
                                })
                                
                    if plate_casc is not None and plate_casc != "unavailable":
                        gray = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)
                        plates = plate_casc.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(30, 10))
                        for (x, y, w, h) in plates:
                            dets.append({
                                "box": [float(x), float(y), float(x+w), float(y+h)],
                                "score": 0.85,
                                "label": "license_plate"
                            })
                except Exception as e:
                    print(f"Error in extra detection: {e}")
            batch_dets.append(dets)
    else:
        batch_dets = [[] for _ in patches]
    return batch_dets
