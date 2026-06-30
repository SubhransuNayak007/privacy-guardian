import os
import yaml
from ultralytics import YOLO

# ==============================================================================
# YOLOv8 Training Script for Face Detection
# ==============================================================================
# This script trains a YOLOv8 model to detect faces in highly complex environments.
# It is highly recommended to use the WIDER FACE dataset or a Roboflow Face 
# Detection dataset formatted in YOLO format: 
# [class_id, x_center, y_center, width, height]
# ==============================================================================

# Directory where your dataset is stored (e.g. WIDER FACE in YOLO format)
DATASET_DIR = "./datasets/face-detection"

def create_yaml_config():
    """Generates the data.yaml file required by Ultralytics YOLOv8."""
    config = {
        "path": os.path.abspath(DATASET_DIR),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "names": {
            0: "face"
        }
    }
    yaml_path = os.path.join(DATASET_DIR, "data.yaml")
    os.makedirs(DATASET_DIR, exist_ok=True)
    with open(yaml_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    print(f"Generated YAML configuration at {yaml_path}")
    return yaml_path

def train_model(yaml_path):
    """Initializes and trains the YOLOv8 Face Detection model."""
    print("Initializing YOLOv8s (Small) model for face detection...")
    # Using YOLOv8s provides a good balance between speed and accuracy for faces
    model = YOLO("yolov8s.pt")
    
    print("Starting face detection training process...")
    # Train the model. GPU is strongly recommended (device=0).
    results = model.train(
        data=yaml_path,
        epochs=100,         # Faces often require more epochs to generalize well
        imgsz=640,          # Standard image size
        batch=16,           # Batch size (reduce if you run out of GPU memory)
        name="face_detector_v1",
        patience=20,        # Early stopping patience
        device="0",         # Use "0" for GPU, or "cpu" for CPU training
        optimizer="AdamW",  # AdamW generally performs well for fine-tuning
        lr0=0.001           # Initial learning rate
    )
    
    print("Training complete!")
    print(f"Model weights saved to: {results.save_dir}/weights/best.pt")

if __name__ == "__main__":
    print("=== YOLOv8 Face Detection Training Pipeline ===")
    yaml_path = create_yaml_config()
    
    # IMPORTANT: Ensure your dataset (e.g. WIDER FACE) is populated in the 
    # DATASET_DIR before uncommenting the line below.
    # train_model(yaml_path)
    
    print("\nNext Steps:")
    print("1. Place your YOLO-formatted face dataset in ./datasets/face-detection/")
    print("2. Ensure images are in images/train and labels are in labels/train.")
    print("3. Uncomment `train_model(yaml_path)` in this script to begin training.")
