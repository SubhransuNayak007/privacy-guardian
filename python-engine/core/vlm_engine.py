import time
import torch
from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image

_vlm_model = None
_vlm_processor = None

def get_vlm_model():
    global _vlm_model, _vlm_processor
    if _vlm_model is None:
        try:
            print("[VLM] Loading Florence-2 model...")
            t0 = time.time()
            model_id = "microsoft/Florence-2-base"
            _vlm_processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
            _vlm_model = AutoModelForCausalLM.from_pretrained(
                model_id,
                trust_remote_code=True,
                torch_dtype=torch.float32, # CPU inference
            )
            print(f"[VLM] Model loaded in {time.time() - t0:.2f}s")
        except Exception as e:
            print(f"[VLM] Error loading model: {e}")
            _vlm_model = "unavailable"
    return _vlm_model, _vlm_processor

def run_vlm_classification(img_array):
    """
    Classify the image using the VLM to extract semantic context.
    Returns a dictionary of findings, e.g., {"doc_type": "Aadhaar", "description": "..."}
    """
    model, processor = get_vlm_model()
    if model == "unavailable" or model is None:
        return {"doc_type": "unknown", "description": ""}

    try:
        # Convert OpenCV BGR to RGB PIL Image
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            # Assuming BGR, but it could be RGB. In main.py it's usually BGR from cv2.
            import cv2
            rgb_img = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_img)
        else:
            image = Image.fromarray(img_array)

        # Florence-2 tasks: <MORE_DETAILED_CAPTION> or <OCR_WITH_REGION>
        # For document classification, a detailed caption usually reveals the document type.
        prompt = "<MORE_DETAILED_CAPTION>"
        
        inputs = processor(text=prompt, images=image, return_tensors="pt")
        
        # CPU generation
        t0 = time.time()
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=50,
            num_beams=3
        )
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        parsed_answer = processor.post_process_generation(generated_text, task=prompt, image_size=(image.width, image.height))
        
        desc = parsed_answer.get(prompt, "").lower()
        print(f"[VLM] Inference completed in {time.time() - t0:.2f}s: {desc}")
        
        doc_type = "unknown"
        if "aadhaar" in desc or "adhaar" in desc:
            doc_type = "aadhaar"
        elif "pan card" in desc or "income tax" in desc:
            doc_type = "pan"
        elif "passport" in desc:
            doc_type = "passport"
        elif "driving license" in desc:
            doc_type = "driving_license"
        elif "credit card" in desc or "debit card" in desc:
            doc_type = "credit_card"
            
        return {"doc_type": doc_type, "description": desc}
        
    except Exception as e:
        print(f"[VLM] Error during inference: {e}")
        return {"doc_type": "unknown", "description": ""}

def run_vlm_ocr(img_array):
    """
    Perform OCR using Florence-2 <OCR_WITH_REGION> task.
    Returns list in format expected by OCR ensemble: [[box, (text, conf)], ...]
    """
    model, processor = get_vlm_model()
    if model == "unavailable" or model is None:
        return []
        
    try:
        import cv2
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            rgb_img = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_img)
        else:
            image = Image.fromarray(img_array)
            
        prompt = "<OCR_WITH_REGION>"
        inputs = processor(text=prompt, images=image, return_tensors="pt")
        
        t0 = time.time()
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            num_beams=3
        )
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        parsed_answer = processor.post_process_generation(generated_text, task=prompt, image_size=(image.width, image.height))
        
        # parsed_answer["<OCR_WITH_REGION>"] usually has "quad_boxes" and "labels"
        results = parsed_answer.get(prompt, {})
        labels = results.get("labels", [])
        quad_boxes = results.get("quad_boxes", [])
        
        combined_result = []
        for i in range(len(labels)):
            text = labels[i]
            box = quad_boxes[i] if i < len(quad_boxes) else None
            if box and len(box) == 8:
                # convert [x1, y1, x2, y2, x3, y3, x4, y4] to [[x,y], ...]
                clean_box = [
                    [float(box[0]), float(box[1])],
                    [float(box[2]), float(box[3])],
                    [float(box[4]), float(box[5])],
                    [float(box[6]), float(box[7])]
                ]
            elif box and len(box) == 4:
                # [xmin, ymin, xmax, ymax]
                clean_box = [
                    [float(box[0]), float(box[1])],
                    [float(box[2]), float(box[1])],
                    [float(box[2]), float(box[3])],
                    [float(box[0]), float(box[3])]
                ]
            else:
                clean_box = [[0,0], [0,0], [0,0], [0,0]]
                
            combined_result.append([clean_box, (str(text), 0.90)])
            
        print(f"[VLM OCR] Extracted {len(combined_result)} regions in {time.time() - t0:.2f}s")
        return combined_result
    except Exception as e:
        print(f"[VLM OCR] Error: {e}")
        return []
