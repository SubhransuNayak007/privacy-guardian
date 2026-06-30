import time
import torch
from transformers import AutoProcessor, LlavaForConditionalGeneration
from PIL import Image

_pixtral_model = None
_pixtral_processor = None

def get_pixtral_model():
    global _pixtral_model, _pixtral_processor
    if _pixtral_model is None:
        try:
            print("[Pixtral] Loading Pixtral-12B model...")
            t0 = time.time()
            model_id = "mistralai/Pixtral-12B-2409"
            
            _pixtral_model = LlavaForConditionalGeneration.from_pretrained(
                model_id, 
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32, 
                device_map="auto" if torch.cuda.is_available() else "cpu"
            )
            _pixtral_processor = AutoProcessor.from_pretrained(model_id)
            print(f"[Pixtral] Model loaded in {time.time() - t0:.2f}s")
        except Exception as e:
            print(f"[Pixtral] Error loading model: {e}")
            _pixtral_model = "unavailable"
    return _pixtral_model, _pixtral_processor

def run_pixtral_classification(img_array):
    model, processor = get_pixtral_model()
    if model == "unavailable" or model is None:
        return {"doc_type": "unknown", "description": ""}
        
    try:
        import cv2
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            rgb_img = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_img)
        else:
            image = Image.fromarray(img_array)
            
        prompt = "USER: <image>\nWhat kind of document is this? (e.g. Aadhaar, PAN card, Passport, Driving License)\nASSISTANT:"
        inputs = processor(text=prompt, images=image, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = inputs.to("cuda")
            
        t0 = time.time()
        generate_ids = model.generate(**inputs, max_new_tokens=30)
        output_text = processor.batch_decode(generate_ids, skip_special_tokens=True)[0]
        
        desc = output_text.lower()
        doc_type = "unknown"
        if "aadhaar" in desc or "adhaar" in desc: doc_type = "aadhaar"
        elif "pan card" in desc or "income tax" in desc: doc_type = "pan"
        elif "passport" in desc: doc_type = "passport"
        elif "driving license" in desc: doc_type = "driving_license"
        
        return {"doc_type": doc_type, "description": desc}
        
    except Exception as e:
        print(f"[Pixtral] Error during inference: {e}")
        return {"doc_type": "unknown", "description": ""}

def run_pixtral_ocr(img_array):
    model, processor = get_pixtral_model()
    if model == "unavailable" or model is None:
        return []
        
    try:
        import cv2
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            rgb_img = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_img)
        else:
            image = Image.fromarray(img_array)
            
        prompt = "USER: <image>\nExtract all text in the image.\nASSISTANT:"
        inputs = processor(text=prompt, images=image, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = inputs.to("cuda")
            
        t0 = time.time()
        generate_ids = model.generate(**inputs, max_new_tokens=512)
        output_text = processor.batch_decode(generate_ids, skip_special_tokens=True)[0]
        
        H, W = img_array.shape[:2]
        clean_box = [[0, 0], [W, 0], [W, H], [0, H]]
        return [[clean_box, (output_text.split("ASSISTANT:")[-1].strip(), 0.85)]]
        
    except Exception as e:
        print(f"[Pixtral] Error during OCR: {e}")
        return []
