import yaml
import os

class ModelRegistry:
    def __init__(self, config_path="config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            return {}
        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)

    def get_detector_model(self):
        return self.config.get("detector", {}).get("model", "yolov8n")
        
    def get_vlm_model(self):
        return self.config.get("vlm", {}).get("model", "florence2-base")
