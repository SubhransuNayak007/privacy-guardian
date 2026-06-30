from models.registry import ModelRegistry

class ModelManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.registry = ModelRegistry()
        self._yolo = None
        self._paddle = None
        self._presidio = None
        self._vlm = None

    def get_yolo(self):
        if self._yolo is None:
            try:
                from ultralytics import YOLO
                model_name = self.registry.get_detector_model()
                self._yolo = YOLO(f"{model_name}.pt")
            except Exception as e:
                print(f"Error loading YOLO: {e}")
                self._yolo = "unavailable"
        return self._yolo

    def get_paddle(self):
        if self._paddle is None:
            try:
                from paddleocr import PaddleOCR
                self._paddle = PaddleOCR(use_angle_cls=True, lang="en", enable_mkldnn=False, cpu_threads=2)
            except Exception as e:
                print(f"Error loading PaddleOCR: {e}")
                self._paddle = "unavailable"
        return self._paddle

    def get_presidio(self):
        if self._presidio is None:
            try:
                from presidio_analyzer import AnalyzerEngine
                self._presidio = AnalyzerEngine()
            except Exception as e:
                print(f"Error loading Presidio: {e}")
                self._presidio = "unavailable"
        return self._presidio

    def get_vlm(self):
        if self._vlm is None:
            try:
                import torch
                from transformers import AutoProcessor, AutoModelForCausalLM
                
                model_name = self.registry.get_vlm_model()
                # microsoft/Florence-2-base
                processor = AutoProcessor.from_pretrained(f"microsoft/{model_name}", trust_remote_code=True)
                model = AutoModelForCausalLM.from_pretrained(f"microsoft/{model_name}", trust_remote_code=True)
                
                device = "cuda" if torch.cuda.is_available() else "cpu"
                model.to(device)
                
                self._vlm = {"model": model, "processor": processor, "device": device}
            except Exception as e:
                print(f"Error loading Florence-2 VLM (Falling back to mock): {e}")
                self._vlm = "florence_mock"
        return self._vlm
        
    def get_status(self):
        return {
            "yolo": "loaded" if self._yolo and self._yolo != "unavailable" else str(self._yolo),
            "paddle": "loaded" if self._paddle and self._paddle != "unavailable" else str(self._paddle),
            "presidio": "loaded" if self._presidio and self._presidio != "unavailable" else str(self._presidio),
            "vlm": "loaded" if self._vlm and self._vlm != "unavailable" else str(self._vlm)
        }
