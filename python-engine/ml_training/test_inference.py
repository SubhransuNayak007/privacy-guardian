from ultralytics import YOLO
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_inference.py <image_path>")
        return
        
    image_path = sys.argv[1]
    
    # Path to your trained model weights
    model_path = "runs/detect/no_plate_detector/weights/best.pt"
    
    try:
        model = YOLO(model_path)
        
        # Run inference
        print(f"Running inference on {image_path}...")
        results = model(image_path)
        
        # Display the results
        for r in results:
            # Print bounding boxes
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                cls_name = model.names[cls_id]
                print(f"Detected {cls_name} with confidence {conf:.2f}")
                
            # Show image
            r.show()  
            
    except Exception as e:
        print(f"Inference failed: {e}")
        print(f"Ensure the model file exists at {model_path} and image exists.")

if __name__ == "__main__":
    main()
