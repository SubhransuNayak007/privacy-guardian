from typing import Dict, Any, List
from .scheduler import TaskGraph, Scheduler
from .fusion import ConfidenceFusion
from .verification import VerificationEngine
from ..detectors.ocr_ensemble import OCREnsemble
from ..nlp.pii_extractor import PIIExtractor
from ..redaction.blur_engine import AdaptiveBlur

class PipelineManager:
    """
    Manages the overall AI Decision Graph for redaction.
    Constructs the DAG (TaskGraph) and executes it via the Scheduler.
    """
    def __init__(self):
        self.graph = TaskGraph()
        self.scheduler = Scheduler(self.graph)
        self.fusion_engine = ConfidenceFusion()
        self.verification_engine = VerificationEngine()
        
        # Instantiate detectors
        self.ocr_ensemble = OCREnsemble()
        self.pii_extractor = PIIExtractor()
        self.blur_engine = AdaptiveBlur()
        
        self._build_graph()
        
    def _build_graph(self):
        # Add OCR Task
        async def run_ocr(state: Dict[str, Any]):
            image = state["image"]
            ocr_result = self.ocr_ensemble.process(image)
            state["ocr_result"] = ocr_result
            state["raw_text"] = ocr_result.get("text", "")
            
        self.graph.add_node("ocr", run_ocr)
        
        # Add PII Extraction Task (Depends on OCR)
        async def run_pii(state: Dict[str, Any]):
            text = state.get("raw_text", "")
            pii_results = self.pii_extractor.extract(text)
            state["pii_results"] = pii_results
            
        self.graph.add_node("pii", run_pii, dependencies=["ocr"])
        
        # Add Vision Task (runs in parallel with OCR)
        async def run_vision(state: Dict[str, Any]):
            # Mock YOLO Vision Detections
            state["vision_results"] = [
                {"label": "FACE", "confidence": 0.98, "bbox": (10, 10, 50, 50)}
            ]
            
        self.graph.add_node("vision", run_vision)
        
        # Add Fusion Task (Depends on PII and Vision)
        async def run_fusion(state: Dict[str, Any]):
            pii_res = state.get("pii_results", [])
            vision_res = state.get("vision_results", [])
            
            final_detections = []
            
            # Example logic: fuse text detections
            for res in pii_res:
                final_conf = self.fusion_engine.compute_final_confidence([res["confidence"], 0.9])
                if final_conf > 0.7:
                    final_detections.append({
                        "label": res["label"],
                        "confidence": final_conf,
                        "bbox": (0, 0, 100, 10) # Mock bbox from PII
                    })
                    
            # Add vision detections directly
            for res in vision_res:
                final_detections.append(res)
                
            state["final_detections"] = final_detections
            
        self.graph.add_node("fusion", run_fusion, dependencies=["pii", "vision"])
        
        # Add Redaction & Verification Task (Depends on Fusion)
        async def run_redact_verify(state: Dict[str, Any]):
            image = state["image"]
            detections = state.get("final_detections", [])
            
            redacted_image = image # Mock blur
            for det in detections:
                redacted_image = self.blur_engine.apply(redacted_image, det["bbox"], det["label"])
                
            # Verify
            is_valid = await self.verification_engine.verify(redacted_image, [state.get("raw_text", "")])
            state["redacted_image"] = redacted_image
            state["verification_passed"] = is_valid
            
        self.graph.add_node("redact_verify", run_redact_verify, dependencies=["fusion"])

    async def process(self, image: Any) -> Dict[str, Any]:
        """
        Executes the AI Decision Graph on the provided image.
        """
        try:
            initial_state = {"image": image}
            final_state = await self.scheduler.execute(initial_state)
            
            return {
                "detections": final_state.get("final_detections", []),
                "verification_passed": final_state.get("verification_passed", False),
                "status": "success" if final_state.get("verification_passed") else "verification_failed"
            }
        except Exception as e:
            # Safely wrap any pipeline errors
            return {
                "detections": [],
                "verification_passed": False,
                "status": "error",
                "error_message": str(e)
            }
