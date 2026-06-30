import numpy as np

_paddle_model = None
_easyocr_model = None

def get_paddle():
    global _paddle_model
    if _paddle_model is None:
        from paddleocr import PaddleOCR
        _paddle_model = PaddleOCR(use_angle_cls=False, lang="en", enable_mkldnn=False, cpu_threads=2)
        print("[OCR] PaddleOCR ready")
    return _paddle_model

def get_easyocr():
    global _easyocr_model
    if _easyocr_model is None:
        try:
            import easyocr
            # We use CPU by default for broader compatibility, can set gpu=True if CUDA is available
            _easyocr_model = easyocr.Reader(['en'], gpu=False)
            print("[OCR] EasyOCR ready")
        except Exception as e:
            print(f"[OCR] EasyOCR unavailable: {e}")
            _easyocr_model = "unavailable"
    return _easyocr_model

class OCREnsemble:
    """
    Intelligent OCR node combining PaddleOCR, EasyOCR, Florence-2 OCR, and Qwen-VL OCR (Stage 2).
    Both engines run and their raw text detections are combined.
    The downstream NLP and NMS deduplication will merge overlapping boxes.
    """
    def __init__(self):
        # Trigger lazy loads
        get_paddle()
        get_easyocr()
        # VLM models are lazy-loaded when called to avoid huge startup latency
        
    def ocr(self, img):
        from core.vlm_engine import run_vlm_ocr
        from core.qwen_engine import run_qwen_ocr
        
        paddle = get_paddle()
        easy = get_easyocr()
        
        combined_result = []
        
        # 1. Run PaddleOCR
        try:
            if hasattr(paddle, "predict"):
                paddle_res = paddle.predict(img)
            else:
                paddle_res = paddle.ocr(img)
                
            if paddle_res and paddle_res[0]:
                if isinstance(paddle_res[0], dict) and "dt_polys" in paddle_res[0]:
                    polys = paddle_res[0].get("dt_polys", [])
                    texts = paddle_res[0].get("rec_texts", [])
                    scores = paddle_res[0].get("rec_scores", [])
                    for i in range(len(texts)):
                        poly = polys[i]
                        box = poly.tolist() if hasattr(poly, "tolist") else list(poly)
                        combined_result.append([box, (texts[i], float(scores[i]))])
                elif isinstance(paddle_res[0], list):
                    for x in paddle_res[0]:
                        if x is not None:
                            combined_result.append(x)
        except Exception as e:
            print(f"[OCR Ensemble] PaddleOCR error: {e}")

        # 2. Run EasyOCR
        if easy != "unavailable":
            try:
                easy_res = easy.readtext(img)
                for detection in easy_res:
                    box, text, conf = detection
                    # format box: float elements to int or float list of lists
                    clean_box = [[float(pt[0]), float(pt[1])] for pt in box]
                    combined_result.append([clean_box, (str(text), float(conf))])
            except Exception as e:
                print(f"[OCR Ensemble] EasyOCR error: {e}")
                
        # 3. Run Florence-2 OCR
        try:
            florence_res = run_vlm_ocr(img)
            if florence_res:
                combined_result.extend(florence_res)
        except Exception as e:
            print(f"[OCR Ensemble] Florence-2 error: {e}")
            
        # 4. Run Qwen-VL OCR
        try:
            qwen_res = run_qwen_ocr(img)
            if qwen_res:
                combined_result.extend(qwen_res)
        except Exception as e:
            print(f"[OCR Ensemble] Qwen-VL error: {e}")
            
        # 5. Run Pixtral OCR
        try:
            from core.pixtral_engine import run_pixtral_ocr
            pixtral_res = run_pixtral_ocr(img)
            if pixtral_res:
                combined_result.extend(pixtral_res)
        except Exception as e:
            print(f"[OCR Ensemble] Pixtral error: {e}")
            
        # Return nested list simulating standard PaddleOCR list return format
        return [combined_result]

    def predict(self, img):
        return self.ocr(img)
