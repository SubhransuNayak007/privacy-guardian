import cv2
import numpy as np
from models.manager import ModelManager

class NsfwService:
    def __init__(self, model_manager: ModelManager):
        self.detector = model_manager.get_nudenet()

    def run_detection(self, img_patch: np.ndarray):
        dets = []
        if self.detector != "unavailable" and self.detector is not None:
            try:
                # NudeNet detect expects image path or numpy array (RGB)
                results = self.detector.detect(img_patch)
                for res in results:
                    score = float(res.get("score", 0.0))
                    if score > 0.4:
                        box = res.get("box", [])
                        if len(box) == 4:
                            # NudeNet v3 returns [x, y, w, h]
                            x1, y1, w, h = box
                            x2, y2 = x1 + w, y1 + h
                            dets.append({
                                "box": [float(x1), float(y1), float(x2), float(y2)],
                                "score": score,
                                "label": "nsfw" # standardize label for our pipeline
                            })
            except Exception as e:
                import logging
                logger = logging.getLogger("privacy_guardian")
                logger.error(f"NudeNet detection error: {e}")
        return dets
