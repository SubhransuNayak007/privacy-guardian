class DecisionRouter:
    def route(self, detections):
        # Determine next steps based on initial detector results
        needs_ocr = any(d["label"] in ["document", "invoice", "passport", "aadhaar", "pan"] for d in detections)
        needs_vlm = any(d["label"] in ["document", "invoice"] and d["score"] < 0.8 for d in detections)
        
        return {
            "run_ocr": needs_ocr,
            "run_vlm": needs_vlm
        }
