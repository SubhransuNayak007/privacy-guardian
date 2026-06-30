import os
import yaml
from ultralytics import YOLO

# ==============================================================================
# YOLOv8 Training Script for Address Block Detection in Images
# ==============================================================================
# This script trains a YOLOv8 model to detect address blocks in documents
# (e.g., shipping labels, envelopes, IDs) using Roboflow or custom layout datasets
# formatted in YOLO format: [class_id, x_center, y_center, width, height]
# ==============================================================================

# Directory where your dataset is stored (downloaded from Roboflow or Kaggle)
DATASET_DIR = "./datasets/address-layout"

def create_yaml_config():
    """Generates the data.yaml file required by Ultralytics YOLOv8."""
    config = {
        "path": os.path.abspath(DATASET_DIR),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {
            0: "address_block",
            1: "name_block",
            2: "date_block",
            3: "signature"
        }
    }
    yaml_path = os.path.join(DATASET_DIR, "data.yaml")
    os.makedirs(DATASET_DIR, exist_ok=True)
    with open(yaml_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    print(f"Generated YAML configuration at {yaml_path}")
    return yaml_path

def train_model(yaml_path):
    """Initializes and trains the YOLOv8 model."""
    print("Initializing YOLOv8n (Nano) model...")
    # Load a pretrained YOLO model (recommended for training)
    model = YOLO("yolov8n.pt")
    
    print("Starting training process...")
    # Train the model. GPU is strongly recommended (device=0).
    results = model.train(
        data=yaml_path,
        epochs=50,          # Adjust based on dataset size and early stopping
        imgsz=640,          # Resize images to 640x640 for training
        batch=16,           # Batch size (reduce if you run out of GPU memory)
        name="address_detector_v1",
        device="0"          # Use "0" for GPU, or "cpu" for CPU training
    )
    
    print("Training complete!")
    print(f"Model weights saved to: {results.save_dir}/weights/best.pt")

if __name__ == "__main__":
    print("=== YOLOv8 Address Detection Training Pipeline ===")
    yaml_path = create_yaml_config()
    
    # IMPORTANT: Ensure your dataset is populated in the DATASET_DIR before uncommenting the line below.
    # train_model(yaml_path)
    
    print("\nNext Steps:")
    print("1. Place your YOLO-formatted dataset in ./datasets/address-layout/")
    print("2. Ensure images are in images/train and labels are in labels/train.")
    print("3. Uncomment `train_model(yaml_path)` in this script to begin training.")
