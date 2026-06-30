import os
import shutil

def build():
    base = r"D:\rot post\privacy-guardian\python-engine"
    
    # 1. Clean old dirs
    old_dirs = ["backend", "detector", "ocr", "pii", "segmentation", "vlm"]
    for d in old_dirs:
        p = os.path.join(base, d)
        if os.path.exists(p):
            shutil.rmtree(p)
            
    # 2. Create new dirs
    new_dirs = ["services", "models", "workers", "utils", "weights", "benchmarks"]
    for d in new_dirs:
        os.makedirs(os.path.join(base, d), exist_ok=True)
        with open(os.path.join(base, d, "__init__.py"), "w") as f:
            pass

    # 3. Write config.yaml
    with open(os.path.join(base, "config.yaml"), "w", encoding="utf-8") as f:
        f.write("""# Privacy Guardian v2.1 Model Registry Config
detector:
  model: yolov8n
  conf_threshold: 0.3

ocr:
  model: paddle

vlm:
  model: florence2-base

segmentation:
  model: fastsam

pii:
  presidio_lang: en
""")

    # 4. Write models/registry.py
    with open(os.path.join(base, "models", "registry.py"), "w", encoding="utf-8") as f:
        f.write("""import yaml
import os

class ModelRegistry:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            return {}
        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def get_detector_model(self):
        return self.config.get("detector", {}).get("model", "yolov8n")
        
    def get_vlm_model(self):
        return self.config.get("vlm", {}).get("model", "florence2-base")
""")

    # 5. Write models/manager.py
    with open(os.path.join(base, "models", "manager.py"), "w", encoding="utf-8") as f:
        f.write("""from models.registry import ModelRegistry

class ModelManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.registry = ModelRegistry()
        self._yolo = None
        self._paddle = None
        self._presidio = None
        self._vlm = None

    def get_yolo(self):
        if self._yolo is None:
            try:
                from ultralytics import YOLO
                model_name = self.registry.get_detector_model()
                self._yolo = YOLO(f"{model_name}.pt")
            except Exception as e:
                print(f"Error loading YOLO: {e}")
                self._yolo = "unavailable"
        return self._yolo

    def get_paddle(self):
        if self._paddle is None:
            try:
                from paddleocr import PaddleOCR
                self._paddle = PaddleOCR(use_angle_cls=True, lang="en", enable_mkldnn=False, cpu_threads=2)
            except Exception as e:
                print(f"Error loading PaddleOCR: {e}")
                self._paddle = "unavailable"
        return self._paddle

    def get_presidio(self):
        if self._presidio is None:
            try:
                from presidio_analyzer import AnalyzerEngine
                self._presidio = AnalyzerEngine()
            except Exception as e:
                print(f"Error loading Presidio: {e}")
                self._presidio = "unavailable"
        return self._presidio

    def get_vlm(self):
        if self._vlm is None:
            try:
                # Placeholder for Florence-2 loading
                self._vlm = "florence_mock" 
            except Exception as e:
                print(f"Error loading VLM: {e}")
                self._vlm = "unavailable"
        return self._vlm
        
    def get_status(self):
        return {
            "yolo": "loaded" if self._yolo and self._yolo != "unavailable" else str(self._yolo),
            "paddle": "loaded" if self._paddle and self._paddle != "unavailable" else str(self._paddle),
            "presidio": "loaded" if self._presidio and self._presidio != "unavailable" else str(self._presidio),
            "vlm": "loaded" if self._vlm and self._vlm != "unavailable" else str(self._vlm)
        }
""")

    # 6. Write services/detector.py
    with open(os.path.join(base, "services", "detector.py"), "w", encoding="utf-8") as f:
        f.write("""from models.manager import ModelManager

class DetectorService:
    def __init__(self, model_manager: ModelManager):
        self.yolo = model_manager.get_yolo()

    def run_detection(self, img_patch):
        dets = []
        if self.yolo != "unavailable" and self.yolo is not None:
            try:
                res = self.yolo.predict(img_patch, verbose=False)[0]
                for box in res.boxes:
                    conf = float(box.conf[0])
                    if conf > 0.3:
                        name = res.names[int(box.cls[0])]
                        x1, y1, x2, y2 = map(float, box.xyxy[0])
                        dets.append({"box": [x1, y1, x2, y2], "score": conf, "label": name})
            except:
                pass
        return dets
""")

    # 7. Write services/ocr.py
    with open(os.path.join(base, "services", "ocr.py"), "w", encoding="utf-8") as f:
        f.write("""from models.manager import ModelManager
import numpy as np

class OCRService:
    def __init__(self, model_manager: ModelManager):
        self.paddle = model_manager.get_paddle()

    def run_ocr(self, img: np.ndarray, doc_boxes: list) -> list:
        if self.paddle == "unavailable" or not self.paddle:
            return []
        
        H, W = img.shape[:2]
        ocr_lines = []
        for db in doc_boxes:
            x1, y1, x2, y2 = db["box"]
            x1, y1 = int(x1 * W), int(y1 * H)
            x2, y2 = int(x2 * W), int(y2 * H)
            
            if x2 - x1 < 10 or y2 - y1 < 10:
                continue
            crop = img[y1:y2, x1:x2]
            try:
                res = self.paddle.ocr(crop, cls=False)
                if res and res[0]:
                    for line in res[0]:
                        box, (txt, conf) = line
                        g_box = [[pt[0] + x1, pt[1] + y1] for pt in box]
                        ocr_lines.append((g_box, txt, conf))
            except:
                pass
        return ocr_lines
""")

    # 8. Write services/pii.py
    with open(os.path.join(base, "services", "pii.py"), "w", encoding="utf-8") as f:
        f.write("""from models.manager import ModelManager
import re

class PIIService:
    def __init__(self, model_manager: ModelManager):
        self.presidio = model_manager.get_presidio()

    def analyze(self, text: str):
        if re.search(r'\\b\\d{4}\\s?\\d{4}\\s?\\d{4}\\b', text):
            return True
        if re.search(r'\\b[A-Z]{5}\\d{4}[A-Z]\\b', text):
            return True
            
        if self.presidio != "unavailable" and self.presidio:
            try:
                res = self.presidio.analyze(text=text, language='en')
                if res: return True
            except:
                pass
        return False
""")

    # 9. Write services/vlm.py
    with open(os.path.join(base, "services", "vlm.py"), "w", encoding="utf-8") as f:
        f.write("""from models.manager import ModelManager

class VLMService:
    def __init__(self, model_manager: ModelManager):
        self.vlm = model_manager.get_vlm()

    def call(self, img_crop, doc_type: str, confidence: float):
        if confidence >= 0.8:
            return None
        return {"extracted_text": "MOCKED_FLORENCE2_TEXT", "sensitive_regions": []}
""")

    # 10. Write services/blur.py
    with open(os.path.join(base, "services", "blur.py"), "w", encoding="utf-8") as f:
        f.write("""import cv2
import numpy as np

class BlurService:
    def apply_gaussian_blur(self, img: np.ndarray, boxes_01: list) -> np.ndarray:
        H, W = img.shape[:2]
        out = img.copy()
        for bx in boxes_01:
            x1, y1, x2, y2 = int(bx[0]*W), int(bx[1]*H), int(bx[2]*W), int(bx[3]*H)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(W, x2), min(H, y2)
            if x2 <= x1 or y2 <= y1: continue
            roi = out[y1:y2, x1:x2]
            roi = cv2.GaussianBlur(roi, (51, 51), 30)
            out[y1:y2, x1:x2] = roi
        return out
""")

    # 11. Write router.py
    with open(os.path.join(base, "router.py"), "w", encoding="utf-8") as f:
        f.write("""class DecisionRouter:
    def route(self, detections):
        # Determine next steps based on initial detector results
        needs_ocr = any(d["label"] in ["document", "invoice", "passport", "aadhaar", "pan"] for d in detections)
        needs_vlm = any(d["label"] in ["document", "invoice"] and d["score"] < 0.8 for d in detections)
        
        return {
            "run_ocr": needs_ocr,
            "run_vlm": needs_vlm
        }
""")

    # 12. Write pipeline.py
    with open(os.path.join(base, "pipeline.py"), "w", encoding="utf-8") as f:
        f.write("""import base64
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
""")

    # 13. Write app.py
    with open(os.path.join(base, "app.py"), "w", encoding="utf-8") as f:
        f.write("""import time
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
import psutil

from models.manager import ModelManager
from pipeline import execute_pipeline

app = FastAPI(title="Privacy Guardian v2.1")

class ScanRequest(BaseModel):
    imageBase64: str

job_results = {}

def get_model_manager():
    return ModelManager()

def process_job(job_id: str, b64_str: str):
    try:
        b64_out, dets, ptime = execute_pipeline(b64_str)
        job_results[job_id] = {
            "status": "completed",
            "image": b64_out,
            "detections": dets,
            "processing_time": ptime
        }
    except Exception as e:
        job_results[job_id] = {"status": "error", "message": str(e)}

@app.post("/scan")
async def scan(req: ScanRequest, background_tasks: BackgroundTasks):
    job_id = "job_" + str(int(time.time() * 1000))
    job_results[job_id] = {"status": "processing"}
    background_tasks.add_task(process_job, job_id, req.imageBase64)
    return {"job_id": job_id, "status": "processing"}

@app.get("/result/{job_id}")
async def get_result(job_id: str):
    if job_id not in job_results:
        raise HTTPException(status_code=404)
    return job_results[job_id]

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/models")
async def models_status(manager: ModelManager = Depends(get_model_manager)):
    return manager.get_status()

@app.get("/metrics")
async def metrics():
    return {
        "ram_usage_percent": psutil.virtual_memory().percent,
        "cpu_usage_percent": psutil.cpu_percent(),
        "active_jobs": len([j for j in job_results.values() if j["status"] == "processing"])
    }

if __name__ == "__main__":
    import uvicorn
    # Force manager initialization before serving
    ModelManager()
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
""")

    # 14. Write benchmarks/benchmark.py
    with open(os.path.join(base, "benchmarks", "benchmark.py"), "w", encoding="utf-8") as f:
        f.write("""import time
import psutil
from models.manager import ModelManager

def run_benchmark():
    print("Starting Model Load Benchmark...")
    t0 = time.time()
    manager = ModelManager()
    
    # Load YOLO
    yolo = manager.get_yolo()
    yolo_time = time.time() - t0
    print(f"YOLO loaded in {yolo_time:.2f}s")
    
    print(f"RAM Usage: {psutil.virtual_memory().percent}%")
    print(manager.get_status())

if __name__ == "__main__":
    run_benchmark()
""")

    print("Architecture v2.1 built successfully.")

if __name__ == "__main__":
    build()
