import base64
import time
import numpy as np
import cv2

from models.manager import ModelManager
from services.detector import DetectorService
from services.ocr import OCRService
from services.pii import PIIService
from services.vlm import VLMService
from services.blur import BlurService
from router import DecisionRouter

def execute_pipeline(b64_str: str):
    t0 = time.time()
    
    # DI Injection
    manager = ModelManager()
    detector = DetectorService(manager)
    ocr = OCRService(manager)
    pii = PIIService(manager)
    vlm = VLMService(manager)
    blur = BlurService()
    decision_router = DecisionRouter()
    
    # 1. Decode
    if b64_str.startswith("data:image"):
        b64_str = b64_str.split(",")[1]
    img_data = base64.b64decode(b64_str)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image")
        
    H, W = img.shape[:2]
    
    # 2. Detect
    raw_dets = detector.run_detection(img)
    
    # Convert to 0-1
    for d in raw_dets:
        d["box"] = [d["box"][0]/W, d["box"][1]/H, d["box"][2]/W, d["box"][3]/H]
        
    # 3. Route
    route_decisions = decision_router.route(raw_dets)
    
    final_dets = list(raw_dets)
    
    # 4. OCR & PII
    if route_decisions["run_ocr"]:
        ocr_lines = ocr.run_ocr(img, [d for d in raw_dets if d["label"] in ["document", "invoice", "passport", "aadhaar", "pan"]])
        for box, txt, conf in ocr_lines:
            if pii.analyze(txt):
                final_dets.append({
                    "box": [min([p[0] for p in box])/W, min([p[1] for p in box])/H, max([p[0] for p in box])/W, max([p[1] for p in box])/H],
                    "label": "pii_text",
                    "score": conf
                })
                
    # 5. VLM Fallback
    if route_decisions["run_vlm"]:
        for d in raw_dets:
            if d["label"] in ["document", "invoice"] and d["score"] < 0.8:
                vlm.call(img, d["label"], d["score"])
                
    # 6. Blur
    blur_boxes = [d["box"] for d in final_dets if d["label"] in ["pii_text", "face", "nsfw"]]
    img_blurred = blur.apply_gaussian_blur(img, blur_boxes)
    
    _, buffer = cv2.imencode('.jpg', img_blurred)
    b64_out = base64.b64encode(buffer).decode('utf-8')
    
    process_time = int((time.time() - t0) * 1000)
    
    return b64_out, final_dets, process_time
