import json
import os
import glob

def convert_coco_to_qlora_jsonl(dataset_dir, output_file):
    """
    Converts a Roboflow COCO dataset into a Hugging Face conversational JSONL format
    suitable for training a Vision-Language Model (VLM) like Florence-2.
    """
    annotations_file = os.path.join(dataset_dir, "train", "_annotations.coco.json")
    if not os.path.exists(annotations_file):
        print(f"No annotations found at {annotations_file}")
        return

    with open(annotations_file, "r") as f:
        coco = json.load(f)

    images = {img["id"]: img for img in coco["images"]}
    categories = {cat["id"]: cat["name"] for cat in coco["categories"]}
    
    # Group annotations by image
    img_anns = {}
    for ann in coco["annotations"]:
        img_id = ann["image_id"]
        if img_id not in img_anns:
            img_anns[img_id] = []
        img_anns[img_id].append(ann)

    with open(output_file, "w") as f_out:
        for img_id, anns in img_anns.items():
            img_info = images[img_id]
            file_name = img_info["file_name"]
            width = img_info["width"]
            height = img_info["height"]
            
            # Florence-2 output format: "<loc_X><loc_Y>... Address"
            # Coordinates are quantized to 0-999
            target_text = ""
            for ann in anns:
                cat_name = categories[ann["category_id"]]
                x, y, w, h = ann["bbox"]
                
                # Quantize coordinates to 1000 bins
                x0 = int((x / width) * 1000)
                y0 = int((y / height) * 1000)
                x1 = int(((x + w) / width) * 1000)
                y1 = int(((y + h) / height) * 1000)
                
                # Clip to 0-999
                x0, y0 = max(0, min(999, x0)), max(0, min(999, y0))
                x1, y1 = max(0, min(999, x1)), max(0, min(999, y1))
                
                # Format specific to Florence-2 region detection
                target_text += f"<loc_{x0}><loc_{y0}><loc_{x1}><loc_{y1}> {cat_name} "

            # Create the conversation
            sample = {
                "image": os.path.join(dataset_dir, "train", file_name),
                "messages": [
                    {"role": "user", "content": "What is the address in this image?"},
                    {"role": "assistant", "content": target_text.strip()}
                ]
            }
            f_out.write(json.dumps(sample) + "\n")
            
    print(f"Successfully converted dataset to {output_file}")

def main():
    # You would iterate through all downloaded datasets here
    # Example:
    datasets = glob.glob("datasets/*/")
    for d in datasets:
        print(f"Processing dataset: {d}")
        convert_coco_to_qlora_jsonl(d, os.path.join(d, "qlora_train.jsonl"))

if __name__ == "__main__":
    main()
