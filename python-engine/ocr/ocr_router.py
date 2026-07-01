import cv2
import numpy as np

_paddle = None
def get_paddle():
    global _paddle
    if _paddle is None:
        try:
            from paddleocr import PaddleOCR
            _paddle = PaddleOCR(
                use_angle_cls=True, 
                lang="en", 
                enable_mkldnn=False, 
                cpu_threads=2,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False
            )
        except Exception:
            _paddle = "unavailable"
    return _paddle

def run_targeted_ocr(img: np.ndarray, doc_boxes: list) -> list:
    paddle = get_paddle()
    if paddle == "unavailable" or not paddle:
        return []
    
    ocr_lines = []
    try:
        # Run OCR on the entire image to ensure we catch all text
        res = paddle.ocr(img)
        if res:
            if isinstance(res, list) and len(res) > 0:
                # 1. PaddleX dict format
                if isinstance(res[0], dict):
                    data = res[0]
                    texts = data.get('rec_texts', [])
                    scores = data.get('rec_scores', [])
                    polys = data.get('rec_polys', [])
                    for txt, conf, poly in zip(texts, scores, polys):
                        box = poly.tolist() if hasattr(poly, 'tolist') else poly
                        ocr_lines.append((box, txt, conf))
                # 2. Standard PaddleOCR format
                elif isinstance(res[0], list):
                    for line in res[0]:
                        if len(line) == 2 and isinstance(line[1], tuple):
                            box, (txt, conf) = line
                            ocr_lines.append((box, txt, conf))
    except Exception as e:
        print(f"Error in OCR: {e}")
        pass
        
    return ocr_lines
