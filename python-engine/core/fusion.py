"""
Confidence fusion logic for the AI Redaction Engine.
"""

class ConfidenceFusion:
    """
    Fuses confidence scores from different models (YOLO, OCR, NER) to compute
    a final, unified confidence score for redaction decisions.
    """
    
    def __init__(self):
        # Base weights for different sources. Higher = more trusted.
        self.weights = {
            "yolo_face": 1.0,
            "yolo_doc": 0.95,
            "yolo_id": 0.95,
            "yolo_plate": 0.95,
            "yolo_sig": 0.95,
            "yolo_logo": 0.95,
            "yolo_safety": 0.95,
            "nudenet": 0.95,
            "insightface": 1.0,
            "mp_face": 0.90,
            "qr": 0.95,
            "ner": 0.90,         # Fine-tuned GLiNER is very accurate for text
            "vlm": 0.85,         # VLM context
            "llm": 0.85,         # LLM logic
            "regex": 0.70,       # Regex is rigid, high recall but moderate precision
            "regex_multi": 0.75,
            "regex_addr": 0.75,
            "address_rules": 0.75,
            "unknown": 0.50
        }

    def compute_final_confidence(self, detections_info: list[tuple[float, str]]) -> float:
        """
        Computes a final confidence score using source-weighted Bayesian fusion.
        Formula: 1 - Product(1 - (P_i * Weight_i))
        
        Args:
            detections_info (list[tuple[float, str]]): List of tuples containing 
                                                       (confidence_0_to_1, source_string)
            
        Returns:
            float: A final combined confidence score between 0.0 and 1.0.
        """
        if not detections_info:
            return 0.0
            
        error_prob = 1.0
        for conf, source in detections_info:
            c = max(0.0, min(1.0, conf))
            w = self.weights.get(source, 0.50)
            
            # Scale the confidence by the trust weight of its source
            weighted_c = c * w
            
            error_prob *= (1.0 - weighted_c)
            
        final_conf = 1.0 - error_prob
        return final_conf

