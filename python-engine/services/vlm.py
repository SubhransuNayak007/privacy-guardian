from models.manager import ModelManager

class VLMService:
    def __init__(self, model_manager: ModelManager):
        self.vlm = model_manager.get_vlm()

    def call(self, img_crop, doc_type: str, confidence: float):
        if confidence >= 0.8:
            return None
        return {"extracted_text": "MOCKED_FLORENCE2_TEXT", "sensitive_regions": []}
