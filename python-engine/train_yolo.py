from ultralytics import YOLO

def train():
    # Load a pre-trained YOLO model (recommended for faster convergence)
    model = YOLO("yolov8n.pt")
    
    # Train the model on our custom dataset
    results = model.train(
        data="dataset.yaml", 
        epochs=30,           # Start with 30 epochs, increase if underfitting
        imgsz=640,           # Standard image size
        device="cpu",        # Use CPU as requested (can take a long time)
        workers=2,           # Keep workers low for CPU stability
        batch=8              # Smaller batch size for CPU
    )
    
    print("Training complete! Model saved to runs/detect/train/weights/best.pt")

if __name__ == "__main__":
    train()
