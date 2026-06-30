from ultralytics import YOLO

def main():
    print("Loading YOLOv8 model...")
    # Load a pretrained YOLO model (recommended for training)
    model = YOLO("yolov8n.pt") 
    
    # Train the model
    # Replace 'data.yaml' with the path to the dataset you downloaded from Roboflow
    print("Starting training...")
    try:
        results = model.train(
            data="data.yaml",   # Path to the dataset configuration file
            epochs=50,          # Number of training epochs
            imgsz=640,          # Image size
            batch=16,           # Batch size
            device="cpu",       # Change to "0" if you have a GPU
            name="no_plate_detector"
        )
        print("Training completed successfully!")
    except Exception as e:
        print(f"Training failed: {e}")
        print("Make sure your dataset is downloaded and the data.yaml path is correct.")

if __name__ == "__main__":
    main()
