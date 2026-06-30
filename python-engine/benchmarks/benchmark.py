import time
import psutil
import numpy as np
try:
    import torch
except ImportError:
    torch = None

from models.manager import ModelManager
from pipeline import execute_pipeline
import cv2

def track_resources():
    ram = psutil.virtual_memory().percent
    cpu = psutil.cpu_percent()
    vram = "N/A"
    gpu = "N/A"
    if torch and torch.cuda.is_available():
        vram = f"{torch.cuda.memory_allocated() / 1e9:.2f} GB"
        gpu = f"{torch.cuda.utilization()}%" if hasattr(torch.cuda, "utilization") else "Unknown %"
    return {"RAM": f"{ram}%", "CPU": f"{cpu}%", "VRAM": vram, "GPU": gpu}

def run_benchmark():
    print("=== Privacy Guardian v2.1 Benchmark ===")
    
    t0 = time.time()
    manager = ModelManager()
    print(f"ModelManager initialization: {time.time() - t0:.2f}s")
    
    # Generate dummy image
    dummy_img = np.random.randint(0, 255, (1024, 1024, 3), dtype=np.uint8)
    
    print("\\n--- Loading Models ---")
    
    t0 = time.time()
    yolo = manager.get_yolo()
    y_time = time.time() - t0
    print(f"YOLO loaded in {y_time:.2f}s")
    
    t0 = time.time()
    paddle = manager.get_paddle()
    p_time = time.time() - t0
    print(f"PaddleOCR loaded in {p_time:.2f}s")
    
    t0 = time.time()
    presidio = manager.get_presidio()
    pr_time = time.time() - t0
    print(f"Presidio loaded in {pr_time:.2f}s")
    
    t0 = time.time()
    vlm = manager.get_vlm()
    v_time = time.time() - t0
    print(f"Florence-2 loaded in {v_time:.2f}s")
    
    print("\\n--- Current Resources ---")
    print(track_resources())
    
    print("\\n--- Inference Benchmarks ---")
    
    # 1. YOLO
    if yolo and yolo != "unavailable":
        t0 = time.time()
        yolo.predict(dummy_img, verbose=False)
        t_yolo = time.time() - t0
        print(f"YOLO Inference: {t_yolo*1000:.1f}ms | {1/t_yolo:.1f} FPS")
    
    # 2. PaddleOCR
    if paddle and paddle != "unavailable":
        t0 = time.time()
        paddle.ocr(dummy_img, cls=False)
        t_paddle = time.time() - t0
        print(f"PaddleOCR Inference: {t_paddle*1000:.1f}ms | {1/t_paddle:.1f} FPS")
        
    # 3. VLM
    if vlm and vlm not in ["unavailable", "florence_mock"]:
        try:
            from PIL import Image
            model = vlm["model"]
            processor = vlm["processor"]
            device = vlm["device"]
            
            pil_img = Image.fromarray(dummy_img)
            task_prompt = "<OCR>"
            inputs = processor(text=task_prompt, images=pil_img, return_tensors="pt").to(device)
            
            t0 = time.time()
            model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=20,
                num_beams=1
            )
            t_vlm = time.time() - t0
            print(f"Florence-2 Inference: {t_vlm*1000:.1f}ms | {1/t_vlm:.1f} FPS")
        except Exception as e:
            print(f"Florence-2 Inference failed: {e}")
            
    print("\\n--- Combined Pipeline Benchmark ---")
    _, buffer = cv2.imencode('.jpg', dummy_img)
    import base64
    b64_str = base64.b64encode(buffer).decode('utf-8')
    
    t0 = time.time()
    try:
        execute_pipeline(b64_str)
        t_pipe = time.time() - t0
        print(f"Pipeline Execution: {t_pipe*1000:.1f}ms | {1/t_pipe:.1f} FPS")
    except Exception as e:
        print(f"Pipeline execution failed: {e}")

    print("\\n--- Final Resources ---")
    print(track_resources())
    
if __name__ == "__main__":
    run_benchmark()
