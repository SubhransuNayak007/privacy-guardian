import time
import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from PIL import Image

_qwen_model = None
_qwen_processor = None

def get_qwen_model():
    global _qwen_model, _qwen_processor
    if _qwen_model is None:
        try:
            print("[Qwen-VL] Loading Qwen2-VL-2B-Instruct model...")
            t0 = time.time()
            model_id = "Qwen/Qwen2-VL-2B-Instruct"
            
            _qwen_model = Qwen2VLForConditionalGeneration.from_pretrained(
                model_id,
                torch_dtype=torch.float32, # CPU by default
                device_map="auto" if torch.cuda.is_available() else "cpu"
            )
            
            _qwen_processor = AutoProcessor.from_pretrained(model_id)
            print(f"[Qwen-VL] Model loaded in {time.time() - t0:.2f}s")
        except Exception as e:
            print(f"[Qwen-VL] Error loading model: {e}")
            _qwen_model = "unavailable"
    return _qwen_model, _qwen_processor

def run_qwen_ocr(img_array):
    """
    Perform OCR using Qwen2-VL-2B-Instruct.
    Since Qwen doesn't easily return bounding boxes for every word unless specifically prompted, 
    we prompt it to extract all text. For bounding boxes, we mock the whole image or let 
    downstream NER match text to Paddle/EasyOCR boxes.
    """
    model, processor = get_qwen_model()
    if model == "unavailable" or model is None:
        return []
        
    try:
        import cv2
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            rgb_img = cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_img)
        else:
            image = Image.fromarray(img_array)
            
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": "Extract all text in the image. Format as a clean string."},
                ],
            }
        ]
        
        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        
        # Simpler approach without qwen_vl_utils
        inputs = processor(
            text=[text],
            images=[image],
            padding=True,
            return_tensors="pt"
        )
        
        if torch.cuda.is_available():
            inputs = inputs.to("cuda")
            
        t0 = time.time()
        generated_ids = model.generate(**inputs, max_new_tokens=512)
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        
        output_text = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )[0]
        
        print(f"[Qwen-VL] OCR completed in {time.time() - t0:.2f}s")
        
        # Since we don't have bounding boxes, we return a single large box spanning the image 
        # so the text is passed to NER/Regex layer. NMS might merge or ignore the box, 
        # but the text gets parsed.
        H, W = img_array.shape[:2]
        clean_box = [[0, 0], [W, 0], [W, H], [0, H]]
        return [[clean_box, (output_text.strip(), 0.85)]]
        
    except Exception as e:
        print(f"[Qwen-VL] Error during OCR: {e}")
        return []
