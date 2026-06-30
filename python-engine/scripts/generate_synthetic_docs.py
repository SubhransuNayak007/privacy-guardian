import os
import random
from PIL import Image, ImageDraw, ImageFont
from faker import Faker

fake = Faker('en_IN')

# YOLO classes based on user preferences for Stage 1 (Better Object Detection)
CLASSES = {
    "Face": 0,
    "PAN": 1,
    "Logo": 2,
    "Signature": 3,
    "Text": 4
}

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def generate_pan_card(output_dir, index):
    """
    Generates a synthetic PAN card with bounding boxes for YOLO training.
    """
    width, height = 800, 500
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    
    # Try to load a standard font, fallback to default if not available
    try:
        font_large = ImageFont.truetype("arial.ttf", 36)
        font_medium = ImageFont.truetype("arial.ttf", 24)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except IOError:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    labels = []

    # Helper function to add a bounding box to YOLO format
    def add_label(class_name, box):
        x1, y1, x2, y2 = box
        # Convert to YOLO format: x_center, y_center, width, height (normalized)
        x_c = ((x1 + x2) / 2) / width
        y_c = ((y1 + y2) / 2) / height
        w = (x2 - x1) / width
        h = (y2 - y1) / height
        labels.append(f"{CLASSES[class_name]} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}")

    # 1. Background elements (India Gov Header)
    draw.rectangle([0, 0, width, 80], fill="#f5f5f5")
    header_text = "INCOME TAX DEPARTMENT"
    
    # Calculate text bounding box (approximate or exact if available)
    bbox = draw.textbbox((150, 20), header_text, font=font_large)
    draw.text((150, 20), header_text, fill="black", font=font_large)
    add_label("Text", bbox)

    # Fake Logo
    logo_box = [20, 10, 80, 70]
    draw.ellipse(logo_box, fill="blue")
    add_label("Logo", logo_box)

    # 2. Fake Face (Gray box placeholder or procedural face)
    face_box = [600, 100, 750, 300]
    draw.rectangle(face_box, fill="gray")
    add_label("Face", face_box)

    # 3. User Details
    name = fake.name()
    father_name = fake.name()
    dob = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime('%d/%m/%Y')
    pan_number = fake.pystr_format(string_format='?????####?')

    # Draw Name
    draw.text((50, 120), "Name", fill="black", font=font_small)
    name_box = draw.textbbox((50, 140), name, font=font_medium)
    draw.text((50, 140), name, fill="black", font=font_medium)
    add_label("Text", name_box)

    # Draw Father's Name
    draw.text((50, 200), "Father's Name", fill="black", font=font_small)
    father_box = draw.textbbox((50, 220), father_name, font=font_medium)
    draw.text((50, 220), father_name, fill="black", font=font_medium)
    add_label("Text", father_box)

    # Draw DOB
    draw.text((50, 280), "Date of Birth", fill="black", font=font_small)
    dob_box = draw.textbbox((50, 300), dob, font=font_medium)
    draw.text((50, 300), dob, fill="black", font=font_medium)
    add_label("Text", dob_box)

    # 4. PAN Number (Crucial PII target)
    draw.text((50, 380), "Permanent Account Number", fill="black", font=font_small)
    pan_box = draw.textbbox((50, 400), pan_number, font=font_large)
    draw.text((50, 400), pan_number, fill="black", font=font_large)
    add_label("PAN", pan_box)

    # 5. Fake Signature
    sig_box = [600, 350, 750, 430]
    draw.line([(610, 390), (640, 360), (660, 420), (690, 370), (740, 400)], fill="black", width=3)
    add_label("Signature", sig_box)

    # Save outputs
    images_dir = os.path.join(output_dir, "images")
    labels_dir = os.path.join(output_dir, "labels")
    create_directory(images_dir)
    create_directory(labels_dir)

    img_path = os.path.join(images_dir, f"pan_{index}.jpg")
    label_path = os.path.join(labels_dir, f"pan_{index}.txt")

    image.save(img_path, "JPEG")
    with open(label_path, "w") as f:
        f.write("\n".join(labels))
        
    return img_path

def main():
    print("Stage 10: Generating Synthetic Datasets for YOLO Training...")
    output_dir = "dataset/synthetic_pan"
    num_samples = 10 # Batch for testing
    
    for i in range(num_samples):
        img_path = generate_pan_card(output_dir, i)
    
    print(f"Successfully generated {num_samples} perfectly labeled synthetic PAN cards at {output_dir}/")

if __name__ == "__main__":
    main()
