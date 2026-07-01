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
    global _face_app
    if _face_app is None:
        try:
            from insightface.app import FaceAnalysis
            _face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
            _face_app.prepare(ctx_id=0, det_size=(640, 640))
        except Exception as e:
            print(f"Error loading insightface: {e}")
            _face_app = "unavailable"
            
    return _face_app, None

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
                                
                        # Run InsightFace specifically on person crops to catch small/distant faces
                        for d in list(dets):
                            if d["label"] == "person":
                                px1, py1, px2, py2 = map(int, d["box"])
                                if px2 - px1 > 20 and py2 - py1 > 20:
                                    person_crop = patch[py1:py2, px1:px2]
                                    if person_crop.size > 0:
                                        p_faces = face_app.get(person_crop)
                                        for pf in p_faces:
                                            pfx1, pfy1, pfx2, pfy2 = pf.bbox
                                            score = float(pf.det_score)
                                            if score > 0.2:
                                                dets.append({
                                                    "box": [float(pfx1 + px1), float(pfy1 + py1), float(pfx2 + px1), float(pfy2 + py1)],
                                                    "score": score,
                                                    "label": "face"
                                                })
                except Exception as e:
                    print(f"Error in extra detection: {e}")
            batch_dets.append(dets)
    else:
        batch_dets = [[] for _ in patches]
    return batch_dets
