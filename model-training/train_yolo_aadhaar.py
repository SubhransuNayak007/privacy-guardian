import os
import yaml
from ultralytics import YOLO

# ==============================================================================
# YOLOv8 Training Script for KYC / Identity Document Regions (Aadhaar Focus)
# ==============================================================================
# This script trains a YOLOv8 object detection model to find precise bounding
# boxes for specific regions on Identity Documents (e.g., Aadhaar cards).
# It isolates the 'aadhaar_number', 'dob', 'name', and 'photo' blocks.
# ==============================================================================

DATASET_DIR = "./datasets/kyc-aadhaar"

def create_yaml_config():
    """Generates the data.yaml file required by Ultralytics YOLOv8."""
    config = {
        "path": os.path.abspath(DATASET_DIR),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {
            0: "aadhaar_number",
            1: "dob",
            2: "name",
            3: "photo",
            4: "vid" # Virtual ID
        }
    }
    yaml_path = os.path.join(DATASET_DIR, "data.yaml")
    os.makedirs(DATASET_DIR, exist_ok=True)
    with open(yaml_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    print(f"Generated YAML configuration at {yaml_path}")
    return yaml_path

def train_model(yaml_path):
    """Initializes and trains the YOLOv8 model for KYC region detection."""
    print("Initializing YOLOv8s model for KYC Document Region Detection...")
    model = YOLO("yolov8s.pt")
    
    print("Starting training process...")
    # Train the model. GPU is strongly recommended.
    results = model.train(
        data=yaml_path,
        epochs=60,          # Standard epochs for layout detection
        imgsz=640,          
        batch=16,           
        name="aadhaar_region_detector_v1",
        device="0"          # Use "0" for GPU, or "cpu" for CPU
    )
    
    print("Training complete!")
    print(f"Model weights saved to: {results.save_dir}/weights/best.pt")
    print("\nNext Step: Use these weights to crop the regions before passing them to EasyOCR.")

if __name__ == "__main__":
    print("=== KYC / Aadhaar Region Detection Training Pipeline ===")
    yaml_path = create_yaml_config()
    
    # IMPORTANT: Ensure your dataset (e.g. Roboflow Aadhaar Card Details Dataset) 
    # is populated in the DATASET_DIR before uncommenting the line below.
    # train_model(yaml_path)
    
    print("\nNext Steps:")
    print("1. Download the 'Aadhaar Card Details' dataset from Roboflow Universe in YOLO format.")
    print("2. Extract to ./datasets/kyc-aadhaar/")
    print("3. Uncomment `train_model(yaml_path)` in this script to begin training.")
