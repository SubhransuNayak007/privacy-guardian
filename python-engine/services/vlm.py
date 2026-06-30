from models.manager import ModelManager

class VLMService:
    def __init__(self, model_manager: ModelManager):
        self.vlm = model_manager.get_vlm()

    def call(self, img_crop, doc_type: str, confidence: float):
        if confidence >= 0.8:
            return None
            
        if self.vlm == "florence_mock" or self.vlm == "unavailable" or not self.vlm:
            return {"extracted_text": "MOCKED_FLORENCE2_TEXT", "sensitive_regions": []}
            
        try:
            from PIL import Image
            import cv2
            
            model = self.vlm["model"]
            processor = self.vlm["processor"]
            device = self.vlm["device"]
            
            # Convert numpy array to PIL Image
            img_rgb = cv2.cvtColor(img_crop, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb)
            
            task_prompt = "<OCR_WITH_REGION>"
            inputs = processor(text=task_prompt, images=pil_img, return_tensors="pt").to(device)
            
            generated_ids = model.generate(
                input_ids=inputs["input_ids"],
                pixel_values=inputs["pixel_values"],
                max_new_tokens=1024,
                num_beams=3
            )
            generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
            parsed_answer = processor.post_process_generation(generated_text, task=task_prompt, image_size=(pil_img.width, pil_img.height))
            
            return {"extracted_text": str(parsed_answer), "sensitive_regions": []}
        except Exception as e:
            print(f"Florence-2 generation failed: {e}")
            return {"extracted_text": "ERROR", "sensitive_regions": []}
