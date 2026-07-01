from typing import List, Dict, Any

_yolo_model = None
_nudenet = None
_insight = None

def get_yolo():
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            # Placeholder for custom fine-tuned YOLO11s
            import os
            model_path = "yolo11s_custom.pt" if os.path.exists("yolo11s_custom.pt") else "yolov8n.pt"
            _yolo_model = YOLO(model_path)
        except Exception:
            _yolo_model = "unavailable"
    return _yolo_model

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
    batch_dets = []
    if not patches:
        return []
    if yolo != "unavailable" and yolo is not None:
        results = yolo.predict(patches, verbose=False)
        for res in results:
            dets = []
            for box in res.boxes:
                conf = float(box.conf[0])
                if conf > 0.3:
                    name = res.names[int(box.cls[0])]
                    x1, y1, x2, y2 = map(float, box.xyxy[0])
                    dets.append({"box": [x1, y1, x2, y2], "score": conf, "label": name})
            batch_dets.append(dets)
    else:
        batch_dets = [[] for _ in patches]
    return batch_dets

