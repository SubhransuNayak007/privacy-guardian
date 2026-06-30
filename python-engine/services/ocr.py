from models.manager import ModelManager
import numpy as np

class OCRService:
    def __init__(self, model_manager: ModelManager):
        self.paddle = model_manager.get_paddle()

    def run_ocr(self, img: np.ndarray, doc_boxes: list) -> list:
        if self.paddle == "unavailable" or not self.paddle:
            return []
        
        H, W = img.shape[:2]
        ocr_lines = []
        for db in doc_boxes:
            x1, y1, x2, y2 = db["box"]
            x1, y1 = int(x1 * W), int(y1 * H)
            x2, y2 = int(x2 * W), int(y2 * H)
            
            if x2 - x1 < 10 or y2 - y1 < 10:
                continue
            crop = img[y1:y2, x1:x2]
            try:
                res = self.paddle.ocr(crop, cls=False)
                if res and res[0]:
                    for line in res[0]:
                        box, (txt, conf) = line
                        g_box = [[pt[0] + x1, pt[1] + y1] for pt in box]
                        ocr_lines.append((g_box, txt, conf))
            except:
                pass
        return ocr_lines
