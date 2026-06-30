import cv2
import numpy as np

_paddle = None
def get_paddle():
    global _paddle
    if _paddle is None:
        try:
            from paddleocr import PaddleOCR
            _paddle = PaddleOCR(use_angle_cls=True, lang="en", enable_mkldnn=False, cpu_threads=2)
        except Exception:
            _paddle = "unavailable"
    return _paddle

def run_targeted_ocr(img: np.ndarray, doc_boxes: list) -> list:
    paddle = get_paddle()
    if paddle == "unavailable" or not paddle:
        return []
    
    H, W = img.shape[:2]
    ocr_lines = []
    
    for db in doc_boxes:
        # Expected box format: 0-1
        x1, y1, x2, y2 = db["box"]
        x1, y1 = int(x1 * W), int(y1 * H)
        x2, y2 = int(x2 * W), int(y2 * H)
        
        # Crop
        if x2 - x1 < 10 or y2 - y1 < 10:
            continue
        crop = img[y1:y2, x1:x2]
        
        try:
            res = paddle.ocr(crop, cls=False)
            if res and res[0]:
                for line in res[0]:
                    box, (txt, conf) = line
                    # Adjust box to global
                    g_box = [[pt[0] + x1, pt[1] + y1] for pt in box]
                    ocr_lines.append((g_box, txt, conf))
        except:
            pass
    return ocr_lines
