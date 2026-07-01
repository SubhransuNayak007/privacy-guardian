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
from services.nsfw import NsfwService
from router import DecisionRouter

def execute_pipeline(b64_str: str):
    t0 = time.time()
    
    # DI Injection
    manager = ModelManager()
    detector = DetectorService(manager)
    ocr = OCRService(manager)
    pii = PIIService(manager)
    vlm = VLMService(manager)
    blur = BlurService(manager)
    nsfw = NsfwService(manager)
    decision_router = DecisionRouter()
    
    # 1. Decode
    if b64_str.startswith("data:image"):
        parts = b64_str.split(",")
        if len(parts) > 1:
            b64_str = parts[1]
    try:
        img_data = base64.b64decode(b64_str)
    except Exception as e:
        raise ValueError("Invalid base64 encoding") from e
        
    nparr = np.frombuffer(img_data, np.uint8)
    if nparr.size == 0:
        raise ValueError("Empty image buffer")
        
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Invalid image")
        
    H, W = img.shape[:2]
    
    # 2. Detect
    raw_dets = []
    if W >= 2048 and H >= 2048:
        # Tile into 4 x 1152x1152 for a 2048x2048 image or similar
        overlap = 128
        tsize = 1152
        tiles = [
            (0, 0, tsize, tsize),
            (W-tsize, 0, W, tsize),
            (0, H-tsize, tsize, H),
            (W-tsize, H-tsize, W, H)
        ]
        boxes_list, scores_list, labels_list = [], [], []
        idx_to_label = {}
        label_to_idx = {}
        
        for (x1, y1, x2, y2) in tiles:
            crop = img[y1:y2, x1:x2]
            dets = detector.run_detection(crop)
            dets.extend(nsfw.run_detection(crop))
            
            for d in dets:
                cx1, cy1, cx2, cy2 = d["box"]
                gx1, gy1, gx2, gy2 = cx1 + x1, cy1 + y1, cx2 + x1, cy2 + y1
                # 0-1 normalize
                gx1, gy1, gx2, gy2 = gx1/W, gy1/H, gx2/W, gy2/H
                
                lbl = d["label"]
                if lbl not in label_to_idx:
                    label_to_idx[lbl] = len(label_to_idx)
                    idx_to_label[label_to_idx[lbl]] = lbl
                
                boxes_list.append([gx1, gy1, gx2, gy2])
                scores_list.append(d["score"])
                labels_list.append(label_to_idx[lbl])
        
        if boxes_list:
            from ensemble_boxes import weighted_boxes_fusion
            # WBF requires list of lists per image
            boxes, scores, labels = weighted_boxes_fusion([boxes_list], [scores_list], [labels_list], weights=None, iou_thr=0.5, skip_box_thr=0.0)
            for b, s, l in zip(boxes, scores, labels):
                raw_dets.append({
                    "box": [float(b[0]*W), float(b[1]*H), float(b[2]*W), float(b[3]*H)],
                    "score": float(s),
                    "label": idx_to_label[int(l)]
                })
    else:
        raw_dets = detector.run_detection(img)
        raw_dets.extend(nsfw.run_detection(img))
    
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
    # Separate bbox blurring vs mask blurring
    blur_boxes = [d["box"] for d in final_dets if d["label"] in ["pii_text", "face", "nsfw", "credit_card", "passport", "license_plate", "gun"]]
    mask_boxes = [d["box"] for d in final_dets if d["label"] in ["tattoo", "signature", "reflection", "intimate_tattoo"]]
    
    img_blurred = img.copy()
    if blur_boxes:
        img_blurred = blur.apply_gaussian_blur(img_blurred, blur_boxes)
    if mask_boxes:
        img_blurred = blur.apply_mask_blur(img_blurred, mask_boxes)
    
    _, buffer = cv2.imencode('.jpg', img_blurred)
    b64_out = base64.b64encode(buffer).decode('utf-8')
    
    process_time = int((time.time() - t0) * 1000)
    
    # 7. Risk Score Logic
    risk_score = 0
    weights = {"passport": 100, "credit_card": 100, "face": 20, "gun": 50, "pii_text": 40, "nsfw": 80, "tattoo": 30, "signature": 50, "intimate_tattoo": 80, "reflection": 15}
    for d in final_dets:
        risk_score += weights.get(d["label"], 10) * d["score"]
    
    risk_level = "low"
    if risk_score > 80: risk_level = "critical"
    elif risk_score > 40: risk_level = "high"
    elif risk_score > 20: risk_level = "medium"
    
    return b64_out, final_dets, process_time, risk_level
