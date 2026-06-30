import cv2
import numpy as np

class VerificationEngine:
    """
    Quality Verification AI.
    Runs OCR on the simulated redacted image to ensure that sensitive information is no longer readable.
    If it is still readable, it suggests escalating the blur padding.
    """
    def __init__(self, ocr_engine_getter=None):
        self.get_ocr = ocr_engine_getter

    async def verify_and_escalate(self, image: np.ndarray, detections: list, max_retries: int = 2) -> list:
        """
        Simulates blurring on the bounding boxes, runs OCR, and checks if sensitive text survives.
        If it does, increases the bounding box size (blur escalation) and retries.
        """
        if not self.get_ocr:
            return detections
            
        H, W = image.shape[:2]
        
        # We only verify text detections that are marked for auto-redaction
        text_dets = [d for d in detections if d.redacted and d.type not in ["face", "qr_code", "barcode", "nudity", "illegal_item"]]
        if not text_dets:
            return detections

        current_dets = detections.copy()
        
        for attempt in range(max_retries):
            # 1. Simulate blur on a copy of the image
            sim_image = image.copy()
            for d in current_dets:
                if d.redacted:
                    x0, y0 = int((d.bbox.x0 / 100) * W), int((d.bbox.y0 / 100) * H)
                    x1, y1 = int((d.bbox.x1 / 100) * W), int((d.bbox.y1 / 100) * H)
                    # Safely bound
                    x0, y0 = max(0, x0), max(0, y0)
                    x1, y1 = min(W, x1), min(H, y1)
                    if x1 > x0 and y1 > y0:
                        roi = sim_image[y0:y1, x0:x1]
                        # Adaptive blur radius based on Stage 8 requirements
                        radius = 18 # default for Text
                        if d.type == "face":
                            radius = 32
                        elif d.type == "passport":
                            radius = 64
                        elif d.type == "signature":
                            radius = 40
                            
                        ksize = (radius * 2) + 1
                        blurred_roi = cv2.GaussianBlur(roi, (ksize, ksize), 0)
                        sim_image[y0:y1, x0:x1] = blurred_roi

            # 2. Re-run OCR
            ocr = self.get_ocr()
            import asyncio
            result = await asyncio.to_thread(lambda: ocr.predict(sim_image) if hasattr(ocr, "predict") else ocr.ocr(sim_image))
            
            # Extract readable text
            readable_texts = set()
            if result and result[0]:
                item = result[0]
                if isinstance(item, dict) and "rec_texts" in item:
                    readable_texts.update(str(t).lower() for t in item.get("rec_texts", []))
                elif isinstance(item, list):
                    for x in item:
                        if x is not None:
                            readable_texts.add(str(x[1][0]).lower())

            # 3. Check for survivals
            failed = False
            for d in current_dets:
                if not d.redacted or d.type not in ["aadhaar", "pan", "phone", "email", "credit_card"]:
                    continue
                d_text_lower = str(d.text).lower()
                
                # Did this specific text survive?
                survived = False
                for r_text in readable_texts:
                    if len(d_text_lower) > 4 and d_text_lower in r_text:
                        survived = True
                        break
                        
                if survived:
                    failed = True
                    # Escalate blur radius by increasing bbox padding by 5%
                    print(f"[Verification] Text survived blur: '{d.text}'. Escalating padding.")
                    d.bbox.x0 = max(0.0, d.bbox.x0 - 5.0)
                    d.bbox.y0 = max(0.0, d.bbox.y0 - 5.0)
                    d.bbox.x1 = min(100.0, d.bbox.x1 + 5.0)
                    d.bbox.y1 = min(100.0, d.bbox.y1 + 5.0)
            
            if not failed:
                print(f"[Verification] All sensitive texts successfully obscured on attempt {attempt + 1}.")
                break
                
        return current_dets
