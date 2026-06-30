import cv2
import os
import glob
import numpy as np

def synthetic_erase_plate(image_path, output_path):
    """
    Given an image of a car, this is a simplified example of how you might
    synthetically 'erase' a license plate if you have its bounding box.
    In a real scenario, you'd use Albumentations or OpenCV to paint over
    the bounding box with the average color of the bumper.
    """
    image = cv2.imread(image_path)
    if image is None:
        return
    
    h, w = image.shape[:2]
    # For demonstration, we simulate erasing a rectangle in the lower-middle
    # where a plate usually is (e.g. y: 70-85%, x: 40-60%)
    pt1 = (int(w * 0.4), int(h * 0.7))
    pt2 = (int(w * 0.6), int(h * 0.85))
    
    # Calculate average color of surrounding bumper to blend it
    # Simplified to a gray box here
    cv2.rectangle(image, pt1, pt2, (128, 128, 128), -1)
    
    cv2.imwrite(output_path, image)
    print(f"Augmented and saved: {output_path}")

def main():
    input_dir = "datasets/normal_cars"
    output_dir = "datasets/synthetic_no_plates"
    
    os.makedirs(output_dir, exist_ok=True)
    
    images = glob.glob(os.path.join(input_dir, "*.jpg"))
    for img_path in images:
        filename = os.path.basename(img_path)
        out_path = os.path.join(output_dir, f"no_plate_{filename}")
        synthetic_erase_plate(img_path, out_path)

if __name__ == "__main__":
    print("Run this script to generate synthetic 'missing plate' data.")
    # main() # Uncomment when input_dir is populated
