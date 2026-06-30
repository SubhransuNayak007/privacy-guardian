import os
import xml.etree.ElementTree as ET
import shutil
import random
from pathlib import Path

# Paths to the downloaded dataset
DATASET_PATH = r"C:\Users\sbhrn\.cache\kagglehub\datasets\dataclusterlabs\indian-number-plates-dataset\versions\3"
ANN_DIR = os.path.join(DATASET_PATH, "Annotations", "Annotations")
IMG_DIR = os.path.join(DATASET_PATH, "Indian_Number_Plates", "Sample_Images")

# Paths for our YOLO formatted dataset
OUTPUT_DIR = "datasets/indian_plates"
os.makedirs(os.path.join(OUTPUT_DIR, "images/train"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "images/val"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "labels/train"), exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "labels/val"), exist_ok=True)

def convert_box(size, box):
    # Convert VOC bounding box to YOLO format
    dw = 1. / size[0]
    dh = 1. / size[1]
    x = (box[0] + box[1]) / 2.0
    y = (box[2] + box[3]) / 2.0
    w = box[1] - box[0]
    h = box[3] - box[2]
    x = x * dw
    w = w * dw
    y = y * dh
    h = h * dh
    return (x, y, w, h)

def process_dataset():
    # Get all xml files
    xml_files = [f for f in os.listdir(ANN_DIR) if f.endswith('.xml')]
    
    # Shuffle for random train/val split
    random.seed(42)
    random.shuffle(xml_files)
    
    split_index = int(len(xml_files) * 0.8)
    train_files = xml_files[:split_index]
    val_files = xml_files[split_index:]
    
    print(f"Total files: {len(xml_files)}")
    print(f"Training: {len(train_files)} | Validation: {len(val_files)}")
    
    for split, files in [("train", train_files), ("val", val_files)]:
        for xml_file in files:
            tree = ET.parse(os.path.join(ANN_DIR, xml_file))
            root = tree.getroot()
            
            img_name = root.find('filename').text
            img_path = os.path.join(IMG_DIR, img_name)
            
            if not os.path.exists(img_path):
                print(f"Image {img_name} not found! Skipping...")
                continue
                
            size = root.find('size')
            w = int(size.find('width').text)
            h = int(size.find('height').text)
            
            if w == 0 or h == 0:
                continue
                
            # YOLO label string
            yolo_labels = []
            for obj in root.iter('object'):
                cls_name = obj.find('name').text
                if cls_name != 'number_plate':
                    continue
                    
                cls_id = 0 # 0 for license plate
                xmlbox = obj.find('bndbox')
                b = (float(xmlbox.find('xmin').text), float(xmlbox.find('xmax').text), 
                     float(xmlbox.find('ymin').text), float(xmlbox.find('ymax').text))
                
                bb = convert_box((w, h), b)
                yolo_labels.append(f"{cls_id} {' '.join([str(a) for a in bb])}")
                
            # If no plates found, skip
            if not yolo_labels:
                continue
                
            # Copy image
            dest_img = os.path.join(OUTPUT_DIR, "images", split, img_name)
            shutil.copy(img_path, dest_img)
            
            # Write label
            label_name = os.path.splitext(img_name)[0] + ".txt"
            dest_label = os.path.join(OUTPUT_DIR, "labels", split, label_name)
            with open(dest_label, "w") as f:
                f.write("\n".join(yolo_labels))

    # Create dataset.yaml
    yaml_content = f"""path: {os.path.abspath(OUTPUT_DIR)}
train: images/train
val: images/val

names:
  0: license_plate
"""
    with open("dataset.yaml", "w") as f:
        f.write(yaml_content)
        
    print("Dataset preparation complete! Ready for training.")

if __name__ == "__main__":
    process_dataset()
