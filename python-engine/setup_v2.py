import os

def build_structure():
    base = r"D:\rot post\privacy-guardian\python-engine"
    
    dirs = [
        "detector", "ocr", "pii", "segmentation", "vlm", "backend", "benchmarks", "datasets", "tests", "docs", "deployment"
    ]
    
    for d in dirs:
        os.makedirs(os.path.join(base, d), exist_ok=True)
        # Create __init__.py
        with open(os.path.join(base, d, "__init__.py"), "w") as f:
            pass

    # 1. detector/image_enhancement.py
    with open(os.path.join(base, "detector", "image_enhancement.py"), "w", encoding="utf-8") as f:
        f.write("""import cv2
import numpy as np
import io
from PIL import Image

def strip_exif(img_data: bytes) -> bytes:
    try:
        image = Image.open(io.BytesIO(img_data))
        data = list(image.getdata())
        image_without_exif = Image.new(image.mode, image.size)
        image_without_exif.putdata(data)
        out = io.BytesIO()
        image_without_exif.save(out, format="JPEG")
        return out.getvalue()
    except Exception:
        return img_data

def check_image_quality(img: np.ndarray) -> bool:
    # Check if too dark or too blurry
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur_val = cv2.Laplacian(gray, cv2.CV_64F).var()
    if blur_val < 10.0:  # arbitrary threshold
        return False
    return True

def enhance_image(img: np.ndarray) -> np.ndarray:
    # CLAHE
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return cv2.cvtColor(clahe.apply(gray), cv2.COLOR_GRAY2BGR)
""")

    # 2. detector/yolo_engine.py
    with open(os.path.join(base, "detector", "yolo_engine.py"), "w", encoding="utf-8") as f:
        f.write("""from typing import List, Dict, Any

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
""")

    # 3. detector/box_fusion.py
    with open(os.path.join(base, "detector", "box_fusion.py"), "w", encoding="utf-8") as f:
        f.write("""def expand_and_merge(all_raw_dets, W, H, overlap=128, expand_px=8):
    # Map coordinates to global 0-1, apply WBF
    try:
        from ensemble_boxes import weighted_boxes_fusion
    except ImportError:
        return all_raw_dets

    if not all_raw_dets:
        return []

    boxes = []
    scores = []
    labels = []
    
    unique_labels = list(set([d["label"] for d in all_raw_dets]))
    label_map = {l: i for i, l in enumerate(unique_labels)}
    rev_map = {i: l for i, l in enumerate(unique_labels)}

    for d in all_raw_dets:
        bx = d["box"]
        # Expand 8px
        x1 = max(0, bx[0] - expand_px) / W
        y1 = max(0, bx[1] - expand_px) / H
        x2 = min(W, bx[2] + expand_px) / W
        y2 = min(H, bx[3] + expand_px) / H
        boxes.append([x1, y1, x2, y2])
        scores.append(d["score"])
        labels.append(label_map[d["label"]])

    mb, ms, ml = weighted_boxes_fusion([boxes], [scores], [labels], weights=None, iou_thr=0.4, skip_box_thr=0.001)
    
    merged = []
    for b, s, l in zip(mb, ms, ml):
        merged.append({
            "box": b, # 0-1 format
            "score": s,
            "label": rev_map[int(l)]
        })
    return merged
""")

    # 4. ocr/ocr_router.py
    with open(os.path.join(base, "ocr", "ocr_router.py"), "w", encoding="utf-8") as f:
        f.write("""import cv2
import numpy as np

_paddle = None
def get_paddle():
    global _paddle
    if _paddle is None:
        try:
            from paddleocr import PaddleOCR
            _paddle = PaddleOCR(use_angle_cls=True, lang="en", enable_mkldnn=False, cpu_threads=2)
        except Exception:
            _paddle = "unavailable"
    return _paddle

def run_targeted_ocr(img: np.ndarray, doc_boxes: list) -> list:
    paddle = get_paddle()
    if paddle == "unavailable" or not paddle:
        return []
    
    H, W = img.shape[:2]
    ocr_lines = []
    
    for db in doc_boxes:
        # Expected box format: 0-1
        x1, y1, x2, y2 = db["box"]
        x1, y1 = int(x1 * W), int(y1 * H)
        x2, y2 = int(x2 * W), int(y2 * H)
        
        # Crop
        if x2 - x1 < 10 or y2 - y1 < 10:
            continue
        crop = img[y1:y2, x1:x2]
        
        try:
            res = paddle.ocr(crop, cls=False)
            if res and res[0]:
                for line in res[0]:
                    box, (txt, conf) = line
                    # Adjust box to global
                    g_box = [[pt[0] + x1, pt[1] + y1] for pt in box]
                    ocr_lines.append((g_box, txt, conf))
        except:
            pass
    return ocr_lines
""")

    # 5. pii/presidio_engine.py
    with open(os.path.join(base, "pii", "presidio_engine.py"), "w", encoding="utf-8") as f:
        f.write("""_presidio = None
def get_presidio():
    global _presidio
    if _presidio is None:
        try:
            from presidio_analyzer import AnalyzerEngine
            _presidio = AnalyzerEngine()
        except:
            _presidio = "unavailable"
    return _presidio

def analyze_text(text: str) -> list:
    p = get_presidio()
    if p == "unavailable" or not p:
        return []
    try:
        return p.analyze(text=text, language='en')
    except:
        return []
""")

    # 6. pii/regex_engine.py
    with open(os.path.join(base, "pii", "regex_engine.py"), "w", encoding="utf-8") as f:
        f.write("""import re

def detect_regex(text: str) -> bool:
    if re.search(r'\\b\\d{4}\\s?\\d{4}\\s?\\d{4}\\b', text): # Aadhaar
        return True
    if re.search(r'\\b[A-Z]{5}\\d{4}[A-Z]\\b', text): # PAN
        return True
    return False
""")

    # 7. pii/risk_score.py
    with open(os.path.join(base, "pii", "risk_score.py"), "w", encoding="utf-8") as f:
        f.write("""def calculate_risk_score(detections: list) -> str:
    score = 0
    for d in detections:
        lbl = d.get("label", "")
        if lbl in ["credit_card", "passport", "pan", "aadhaar"]:
            score += 100
        elif lbl in ["face"]:
            score += 20
        elif lbl in ["qr", "barcode"]:
            score += 40
        elif lbl in ["phone", "email"]:
            score += 10
            
    if score >= 100:
        return "High"
    elif score >= 50:
        return "Medium"
    else:
        return "Low"
""")

    # 8. vlm/vlm_router.py
    with open(os.path.join(base, "vlm", "vlm_router.py"), "w", encoding="utf-8") as f:
        f.write("""def call_vlm(img_crop, doc_type: str, confidence: float):
    # Conditional loading of Florence-2
    # Only triggered if confidence < 0.8 on a complex doc
    if confidence >= 0.8:
        return None
        
    print(f"Triggering Tier-2 VLM for {doc_type} due to low confidence ({confidence})...")
    # MOCK implementation to prevent VRAM overflow on standard servers
    return {"extracted_text": "MOCKED_VLM_TEXT", "sensitive_regions": []}
""")

    # 9. segmentation/blur.py
    with open(os.path.join(base, "segmentation", "blur.py"), "w", encoding="utf-8") as f:
        f.write("""import cv2
import numpy as np

def apply_gaussian_blur(img: np.ndarray, boxes_01: list) -> np.ndarray:
    H, W = img.shape[:2]
    out = img.copy()
    for bx in boxes_01:
        x1, y1, x2, y2 = int(bx[0]*W), int(bx[1]*H), int(bx[2]*W), int(bx[3]*H)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(W, x2), min(H, y2)
        if x2 <= x1 or y2 <= y1:
            continue
        roi = out[y1:y2, x1:x2]
        roi = cv2.GaussianBlur(roi, (51, 51), 30)
        out[y1:y2, x1:x2] = roi
    return out
""")

    print("Setup v2 completed successfully.")

if __name__ == "__main__":
    build_structure()
