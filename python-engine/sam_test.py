import cv2
import numpy as np
from ultralytics import SAM

def test_sam():
    # Create a dummy image
    img = np.zeros((500, 500, 3), dtype=np.uint8)
    cv2.circle(img, (250, 250), 100, (255, 255, 255), -1)

    model = SAM('mobile_sam.pt')
    
    # Bounding box covering the circle
    bboxes = [[150, 150, 350, 350]]
    
    results = model.predict(img, bboxes=bboxes, verbose=False)
    
    print("Num results:", len(results))
    if results[0].masks is not None:
        xy = results[0].masks.xy
        print("Num masks in result 0:", len(xy))
        print("Mask 0 shape:", xy[0].shape)
    else:
        print("No masks returned")

if __name__ == "__main__":
    test_sam()
