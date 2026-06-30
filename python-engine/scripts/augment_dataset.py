import os
import cv2
import albumentations as A
import glob

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

def get_augmentation_pipeline():
    """
    Creates an extreme augmentation pipeline simulating real-world document scanning conditions:
    Night, Motion Blur, Rain, Folded/Warped, Rotated, Dirty, Scanned, Low Light, JPEG artifacts.
    """
    return A.Compose([
        A.OneOf([
            A.MotionBlur(p=1.0),
            A.GaussianBlur(blur_limit=(3, 7), p=1.0),
        ], p=0.3),
        
        A.OneOf([
            A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=1.0),
            A.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.1, p=1.0),
            A.ToGray(p=1.0)
        ], p=0.5), # Low light / Night / Scanned
        
        A.RandomRain(p=0.1), # Rain
        
        A.OneOf([
            A.ElasticTransform(alpha=1, sigma=50, alpha_affine=50, p=1.0),
            A.GridDistortion(p=1.0),
            A.OpticalDistortion(distort_limit=1, shift_limit=0.5, p=1.0)
        ], p=0.4), # Folded / Warped
        
        A.ShiftScaleRotate(shift_limit=0.0625, scale_limit=0.1, rotate_limit=45, p=0.5, border_mode=cv2.BORDER_CONSTANT, value=(255, 255, 255)), # Rotated
        
        A.OneOf([
            A.GaussNoise(var_limit=(10.0, 50.0), p=1.0),
            A.MultiplicativeNoise(multiplier=(0.9, 1.1), elementwise=True, p=1.0)
        ], p=0.4), # Dirty / Scanned
        
        A.ImageCompression(quality_lower=10, quality_upper=50, p=0.3) # JPEG Artifacts
    ], bbox_params=A.BboxParams(format='yolo', min_visibility=0.3, label_fields=['class_labels']))

def process_dataset(input_dir, output_dir, num_augmentations=3):
    """
    Reads synthetic dataset and applies extreme augmentations.
    """
    images_dir = os.path.join(input_dir, "images")
    labels_dir = os.path.join(input_dir, "labels")
    
    out_images_dir = os.path.join(output_dir, "images")
    out_labels_dir = os.path.join(output_dir, "labels")
    
    create_directory(out_images_dir)
    create_directory(out_labels_dir)
    
    transform = get_augmentation_pipeline()
    
    image_files = glob.glob(os.path.join(images_dir, "*.jpg"))
    if not image_files:
        print(f"No images found in {images_dir}")
        return
        
    print(f"Found {len(image_files)} images. Augmenting {num_augmentations} times each...")
    
    for img_path in image_files:
        filename = os.path.basename(img_path)
        name, ext = os.path.splitext(filename)
        label_path = os.path.join(labels_dir, f"{name}.txt")
        
        # Read image
        image = cv2.imread(img_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Read labels
        bboxes = []
        class_labels = []
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                for line in f.readlines():
                    parts = line.strip().split()
                    if len(parts) == 5:
                        c, x, y, w, h = parts
                        bboxes.append([float(x), float(y), float(w), float(h)])
                        class_labels.append(int(c))
        
        # Save original copy to output too
        cv2.imwrite(os.path.join(out_images_dir, f"{name}_orig{ext}"), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        with open(os.path.join(out_labels_dir, f"{name}_orig.txt"), 'w') as f:
            for bbox, c in zip(bboxes, class_labels):
                f.write(f"{c} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}\n")

        # Apply augmentations
        for i in range(num_augmentations):
            try:
                transformed = transform(image=image, bboxes=bboxes, class_labels=class_labels)
                transformed_image = transformed['image']
                transformed_bboxes = transformed['bboxes']
                transformed_class_labels = transformed['class_labels']
                
                aug_name = f"{name}_aug{i}"
                cv2.imwrite(os.path.join(out_images_dir, f"{aug_name}{ext}"), cv2.cvtColor(transformed_image, cv2.COLOR_RGB2BGR))
                
                with open(os.path.join(out_labels_dir, f"{aug_name}.txt"), 'w') as f:
                    for bbox, c in zip(transformed_bboxes, transformed_class_labels):
                        f.write(f"{c} {bbox[0]:.6f} {bbox[1]:.6f} {bbox[2]:.6f} {bbox[3]:.6f}\n")
            except Exception as e:
                # Albumentations might fail if bounding boxes go completely out of bounds depending on the transform
                print(f"Skipping augmentation {i} for {filename} due to bbox bounds error: {e}")

def main():
    print("Stage 9: Extreme Data Augmentation Pipeline")
    input_dir = "dataset/synthetic_pan"
    output_dir = "dataset/augmented_pan"
    
    process_dataset(input_dir, output_dir, num_augmentations=5)
    
    print(f"Successfully generated augmented datasets in {output_dir}/")

if __name__ == "__main__":
    main()
