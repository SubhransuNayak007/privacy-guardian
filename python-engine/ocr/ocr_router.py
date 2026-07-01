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
    
    ocr_lines = []
    try:
        # Run OCR on the entire image to ensure we catch all text,
        # even if YOLO failed to detect a "document" box.
        res = paddle.ocr(img, cls=False)
        if res and res[0]:
            for line in res[0]:
                box, (txt, conf) = line
                ocr_lines.append((box, txt, conf))
    except Exception as e:
        print(f"Error in OCR: {e}")
        pass
        
    return ocr_lines
