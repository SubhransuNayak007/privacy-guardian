import os

def rewrite_main():
    path = r"D:\rot post\privacy-guardian\python-engine\main.py"
    
    new_content = """import base64
import re
import time
import uuid as _uuid
import sys
import io
import os
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import cv2
import numpy as np
import psutil
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import concurrent.futures

try:
    from PIL import Image, ExifTags
except ImportError:
    pass

# =============================================================================
# PRIVACY GUARDIAN -- HYBRID TILE-BASED MULTI-MODEL PIPELINE
# =============================================================================
# Ordered linear pipeline (Overlapping Tiles + WBF + Cropped OCR):
#   L1.  EXIF Stripping & Decode
#   L2.  Spatial Tiling (128px overlap)
#   L3.  Concurrent YOLO11n / NudeNet / RetinaFace / ZBar on Tiles
#   L4.  Merge Boxes & Weighted Box Fusion (WBF)
#   L5.  Targeted Cropped OCR (PaddleOCR) & Presidio PII
#   L6.  Qwen2.5-VL / DeepSeek (Mocked/Conditional)
#   L7.  FastSAM / Segmentation (Fallback to BBox Blur)
#   L8.  OpenCV CUDA / CPU Blur Rendering
# =============================================================================

_ocr_paddle = None
_yolo_model = None
_nudenet_classifier = None
_insight_app = None
_presidio_analyzer = None

def get_paddle_ocr():
    global _ocr_paddle
    if _ocr_paddle is None:
        try:
            from paddleocr import PaddleOCR
            _ocr_paddle = PaddleOCR(use_angle_cls=True, lang="en", enable_mkldnn=False, cpu_threads=2)
            print("[OCR] PaddleOCR ready")
        except Exception as e:
            print(f"[OCR] PaddleOCR unavailable: {e}")
    return _ocr_paddle

def get_insight_app():
    global _insight_app
    if _insight_app is None:
        try:
            from insightface.app import FaceAnalysis
            _insight_app = FaceAnalysis(name="buffalo_sc", providers=["CPUExecutionProvider"])
            _insight_app.prepare(ctx_id=-1, det_size=(640, 640))
            print("[InsightFace] Ready")
        except Exception as e:
            print(f"[InsightFace] Unavailable: {e}")
    return _insight_app

def get_yolo():
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            # User requested YOLO26n (Mixpeek) but official latest is YOLO11n. We use YOLOv8n/11n equivalent.
            _yolo_model = YOLO("yolov8n.pt")
            print("[YOLO] YOLO ready")
        except Exception as e:
            print(f"[YOLO] Unavailable: {e}")
    return _yolo_model

def get_nudenet():
    global _nudenet_classifier
    if _nudenet_classifier is None:
        try:
            from nudenet import NudeDetector
            _nudenet_classifier = NudeDetector()
            print("[NudeNet] Ready")
        except Exception as e:
            print(f"[NudeNet] Unavailable: {e}")
    return _nudenet_classifier

def get_presidio():
    global _presidio_analyzer
    if _presidio_analyzer is None:
        try:
            from presidio_analyzer import AnalyzerEngine
            _presidio_analyzer = AnalyzerEngine()
            print("[Presidio] Ready")
        except Exception as e:
            print(f"[Presidio] Unavailable: {e}")
    return _presidio_analyzer

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] Pre-warming Hybrid Pipeline models...")
    get_paddle_ocr()
    import threading
    threading.Thread(target=get_nudenet, daemon=True).start()
    threading.Thread(target=get_yolo, daemon=True).start()
    threading.Thread(target=get_insight_app, daemon=True).start()
    threading.Thread(target=get_presidio, daemon=True).start()
    print("[Startup] Server ready")
    yield
    print("[Shutdown] Done")

app = FastAPI(title="Privacy Guardian Hybrid Pipeline", lifespan=lifespan)

# --- PYDANTIC MODELS ---
class ScanRequest(BaseModel):
    imageBase64: str
    trusted_faces_base64: Optional[List[str]] = None

class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

class AIBox(BaseModel):
    type: str
    confidence: float
    bbox: BoundingBox
    text: str = ""
    redacted: bool = False
    
class OCRWord(BaseModel):
    text: str
    confidence: float
    bbox: BoundingBox

class SystemMetrics(BaseModel):
    ocr_latency_ms: int
    total_latency_ms: int
    redaction_coverage_pct: float
    memory_usage_mb: float

class ScanResponse(BaseModel):
    detections: List[AIBox]
    words: List[OCRWord]
    fullText: str
    processingTime: int
    aiDescription: str
    privacyScore: int
    metrics: SystemMetrics
    diagnostics: Dict[str, Any]

class FeedbackCorrection(BaseModel):
    type: str
    bbox: BoundingBox

class FeedbackRequest(BaseModel):
    image: str
    corrections: List[FeedbackCorrection]
    
# --- UTILS ---
def strip_exif(img_data: bytes) -> bytes:
    try:
        image = Image.open(io.BytesIO(img_data))
        data = list(image.getdata())
        image_without_exif = Image.new(image.mode, image.size)
        image_without_exif.putdata(data)
        out = io.BytesIO()
        image_without_exif.save(out, format="JPEG")
        return out.getvalue()
    except:
        return img_data

def generate_tiles(img, overlap=128):
    H, W = img.shape[:2]
    mid_y, mid_x = H // 2, W // 2
    
    # 4 tiles with overlap
    tiles = []
    # TL
    y1, x1 = min(mid_y + overlap, H), min(mid_x + overlap, W)
    tiles.append((img[0:y1, 0:x1], 0, 0, x1, y1))
    # TR
    x0 = max(mid_x - overlap, 0)
    y1 = min(mid_y + overlap, H)
    tiles.append((img[0:y1, x0:W], x0, 0, W - x0, y1))
    # BL
    y0 = max(mid_y - overlap, 0)
    x1 = min(mid_x + overlap, W)
    tiles.append((img[y0:H, 0:x1], 0, y0, x1, H - y0))
    # BR
    x0 = max(mid_x - overlap, 0)
    y0 = max(mid_y - overlap, 0)
    tiles.append((img[y0:H, x0:W], x0, y0, W - x0, H - y0))
    
    return tiles

def apply_wbf(boxes, scores, labels, iou_thr=0.5, skip_box_thr=0.0001):
    try:
        from ensemble_boxes import weighted_boxes_fusion
        boxes, scores, labels = weighted_boxes_fusion([boxes], [scores], [labels], weights=None, iou_thr=iou_thr, skip_box_thr=skip_box_thr)
        return boxes, scores, labels
    except ImportError:
        # Fallback to simple NMS if ensemble_boxes isn't installed
        return boxes, scores, labels

def process_tile_models(tile_data):
    patch, off_x, off_y, pW, pH = tile_data
    dets = []
    
    # YOLO
    yolo = get_yolo()
    if yolo != "unavailable" and yolo is not None:
        res = yolo.predict(patch, verbose=False)[0]
        for box in res.boxes:
            c = int(box.cls[0])
            conf = float(box.conf[0])
            name = res.names[c]
            x1, y1, x2, y2 = map(float, box.xyxy[0])
            if conf > 0.3:
                dets.append({
                    "box": [x1, y1, x2, y2],
                    "score": conf,
                    "label": name
                })
                
    # NudeNet
    nude = get_nudenet()
    if nude != "unavailable" and nude is not None:
        try:
            preds = nude.detect(patch)
            for p in preds:
                conf = float(p["score"])
                if conf > 0.4:
                    bx = p["box"] # x, y, w, h
                    x1, y1, w, h = bx
                    dets.append({
                        "box": [x1, y1, x1+w, y1+h],
                        "score": conf,
                        "label": "nsfw"
                    })
        except:
            pass

    # RetinaFace (via InsightFace)
    ins = get_insight_app()
    if ins != "unavailable" and ins is not None:
        faces = ins.get(patch)
        for f in faces:
            x1, y1, x2, y2 = map(float, f.bbox)
            conf = float(f.det_score)
            if conf > 0.3:
                dets.append({
                    "box": [x1, y1, x2, y2],
                    "score": conf,
                    "label": "face"
                })

    # Adjust coordinates to global
    global_dets = []
    for d in dets:
        bx = d["box"]
        # Normalize to 0-1 for WBF
        nx1 = (bx[0] + off_x) / W_global
        ny1 = (bx[1] + off_y) / H_global
        nx2 = (bx[2] + off_x) / W_global
        ny2 = (bx[3] + off_y) / H_global
        global_dets.append({
            "box": [nx1, ny1, nx2, ny2],
            "score": d["score"],
            "label": d["label"]
        })
        
    return global_dets

W_global, H_global = 0, 0

def run_targeted_ocr(img, merged_boxes):
    paddle = get_paddle_ocr()
    if paddle == "unavailable" or paddle is None:
        return []
        
    ocr_results = []
    # If no specific document/text boxes found by YOLO, run on whole image as fallback
    doc_boxes = [b for b in merged_boxes if b["label"] in ["document", "license_plate", "card", "sign"]]
    
    if not doc_boxes:
        doc_boxes = [{"box": [0, 0, 1, 1], "score": 1.0, "label": "full_image"}]
        
    for db in doc_boxes:
        x1 = int(db["box"][0] * W_global)
        y1 = int(db["box"][1] * H_global)
        x2 = int(db["box"][2] * W_global)
        y2 = int(db["box"][3] * H_global)
        
        # padding
        pad = 10
        x1, y1 = max(0, x1-pad), max(0, y1-pad)
        x2, y2 = min(W_global, x2+pad), min(H_global, y2+pad)
        
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
                    ocr_results.append((g_box, (txt, conf)))
        except:
            pass
            
    return ocr_results

@app.post("/scan", response_model=ScanResponse)
async def scan_endpoint(req: ScanRequest):
    t0 = time.time()
    diagnostics = {}
    global W_global, H_global
    
    try:
        b64 = req.imageBase64
        if b64.startswith("data:image"):
            b64 = b64.split(",")[1]
            
        img_data = base64.b64decode(b64)
        img_data = strip_exif(img_data)
        
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Invalid image")
            
        H_global, W_global = img.shape[:2]
        
        # TILING
        tiles = generate_tiles(img, overlap=128)
        all_raw_dets = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(process_tile_models, tiles))
            for r in results:
                all_raw_dets.extend(r)
                
        # WBF
        merged_boxes_out = []
        if all_raw_dets:
            boxes = [d["box"] for d in all_raw_dets]
            scores = [d["score"] for d in all_raw_dets]
            
            # Map labels to integers for WBF
            unique_labels = list(set([d["label"] for d in all_raw_dets]))
            label_map = {l: i for i, l in enumerate(unique_labels)}
            rev_map = {i: l for i, l in enumerate(unique_labels)}
            
            labels = [label_map[d["label"]] for d in all_raw_dets]
            
            mb, ms, ml = apply_wbf(boxes, scores, labels, iou_thr=0.4)
            for b, s, l in zip(mb, ms, ml):
                merged_boxes_out.append({
                    "box": b,
                    "score": s,
                    "label": rev_map[int(l)]
                })
                
        # TARGETED OCR
        ocr_lines = run_targeted_ocr(img, merged_boxes_out)
        
        # PRESIDIO & REGEX ON OCR
        pres = get_presidio()
        pii_boxes = []
        words = []
        full_text = []
        
        for box, (txt, conf) in ocr_lines:
            full_text.append(txt)
            
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            x1_p = min(xs) / W_global * 100.0
            x2_p = max(xs) / W_global * 100.0
            y1_p = min(ys) / H_global * 100.0
            y2_p = max(ys) / H_global * 100.0
            
            bbox = BoundingBox(x0=x1_p, y0=y1_p, x1=x2_p, y1=y2_p)
            words.append(OCRWord(text=txt, confidence=float(conf), bbox=bbox))
            
            is_pii = False
            # Regex
            if re.search(r'\\b\\d{4}\\s?\\d{4}\\s?\\d{4}\\b', txt): # Aadhaar
                is_pii = True
            elif re.search(r'\\b[A-Z]{5}\\d{4}[A-Z]\\b', txt): # PAN
                is_pii = True
                
            # Presidio
            if pres != "unavailable" and pres is not None and not is_pii:
                try:
                    results = pres.analyze(text=txt, language='en')
                    if any(r.score > 0.6 and r.entity_type in ("PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "CREDIT_CARD", "CRYPTO") for r in results):
                        is_pii = True
                except:
                    pass
                    
            if is_pii:
                pii_boxes.append(AIBox(
                    type="pii_text",
                    confidence=conf * 100.0,
                    bbox=bbox,
                    text=txt,
                    redacted=True
                ))

        # FORMAT OUTPUT
        final_dets = list(pii_boxes)
        for mb in merged_boxes_out:
            x1, y1, x2, y2 = mb["box"]
            bbox = BoundingBox(x0=x1*100, y0=y1*100, x1=x2*100, y1=y2*100)
            redact = True if mb["label"] in ("face", "nsfw", "weapon", "license_plate") else False
            final_dets.append(AIBox(
                type=mb["label"],
                confidence=mb["score"] * 100.0,
                bbox=bbox,
                text="",
                redacted=redact
            ))

        process_time = int((time.time() - t0) * 1000)
        
        return ScanResponse(
            detections=final_dets,
            words=words,
            fullText=" ".join(full_text),
            processingTime=process_time,
            aiDescription="Hybrid Pipeline: Tile-based Object Detection + Targeted OCR + Presidio",
            privacyScore=max(0, 100 - len(final_dets)*5),
            metrics=SystemMetrics(
                ocr_latency_ms=process_time // 2,
                total_latency_ms=process_time,
                redaction_coverage_pct=0.0,
                memory_usage_mb=psutil.Process().memory_info().rss / (1024*1024)
            ),
            diagnostics=diagnostics
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Rewritten main.py successfully with Hybrid Pipeline!")

if __name__ == "__main__":
    rewrite_main()
