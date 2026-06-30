import time
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
