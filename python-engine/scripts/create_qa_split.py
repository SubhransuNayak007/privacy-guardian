import os
import shutil
import random
from pathlib import Path

# Stage 12: Human QA Dataset
# This script ensures that 5,000 images are strictly moved to dataset/qa_hidden/
# and guarantees they are never touched by the training or augmentation scripts.

def create_qa_split(source_dir, target_dir, num_samples=5000):
    print(f"Creating hidden QA split of {num_samples} images...")
    
    source_images = Path(source_dir) / "images"
    source_labels = Path(source_dir) / "labels"
    
    target_images = Path(target_dir) / "images"
    target_labels = Path(target_dir) / "labels"
    
    if not source_images.exists():
        print(f"Source directory {source_images} does not exist.")
        return
        
    target_images.mkdir(parents=True, exist_ok=True)
    target_labels.mkdir(parents=True, exist_ok=True)
    
    # Get all images
    all_images = list(source_images.glob("*.jpg"))
    if not all_images:
        print("No images found in source.")
        return
        
    print(f"Found {len(all_images)} total images in source.")
    
    if len(all_images) < num_samples:
        print(f"Warning: Only {len(all_images)} images available, moving all to QA.")
        num_samples = len(all_images)
        
    # Randomly select samples
    qa_samples = random.sample(all_images, num_samples)
    
    moved = 0
    for img_path in qa_samples:
        img_name = img_path.name
        lbl_name = img_path.stem + ".txt"
        lbl_path = source_labels / lbl_name
        
        # Move image
        shutil.move(str(img_path), str(target_images / img_name))
        
        # Move label if it exists
        if lbl_path.exists():
            shutil.move(str(lbl_path), str(target_labels / lbl_name))
            
        moved += 1
        if moved % 100 == 0:
            print(f"Moved {moved} files...")
            
    print(f"Successfully moved {moved} files to {target_dir}")
    print(f"These files must NEVER be used in training to prevent overfitting.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create a hidden QA dataset split")
    parser.add_argument("--source", type=str, default="../dataset/synthetic", help="Source dataset directory")
    parser.add_argument("--target", type=str, default="../dataset/qa_hidden", help="Target hidden QA directory")
    parser.add_argument("--num", type=int, default=5000, help="Number of samples to move")
    args = parser.parse_args()
    
    # Ensure run from scripts folder
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    create_qa_split(args.source, args.target, args.num)
