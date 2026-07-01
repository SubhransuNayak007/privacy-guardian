import cv2
import numpy as np
from models.manager import ModelManager

class BlurService:
    def __init__(self, model_manager: ModelManager = None):
        self.model_manager = model_manager

    def apply_gaussian_blur(self, img: np.ndarray, boxes_01: list) -> np.ndarray:
        H, W = img.shape[:2]
        out = img.copy()
        for bx in boxes_01:
            x1, y1, x2, y2 = int(bx[0]*W), int(bx[1]*H), int(bx[2]*W), int(bx[3]*H)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(W, x2), min(H, y2)
            if x2 <= x1 or y2 <= y1: continue
            roi = out[y1:y2, x1:x2]
            roi = cv2.GaussianBlur(roi, (51, 51), 30)
            out[y1:y2, x1:x2] = roi
        return out

    def apply_mask_blur(self, img: np.ndarray, boxes_01: list) -> np.ndarray:
        if not self.model_manager:
            return self.apply_gaussian_blur(img, boxes_01)
            
        fastsam = self.model_manager.get_fastsam()
        if fastsam == "unavailable" or fastsam is None:
            return self.apply_gaussian_blur(img, boxes_01)
            
        H, W = img.shape[:2]
        pixel_boxes = []
        for bx in boxes_01:
            x1, y1, x2, y2 = int(bx[0]*W), int(bx[1]*H), int(bx[2]*W), int(bx[3]*H)
            pixel_boxes.append([x1, y1, x2, y2])
            
        try:
            results = fastsam(img, bboxes=pixel_boxes, verbose=False)
            if len(results) > 0 and results[0].masks is not None:
                masks = results[0].masks.data.cpu().numpy()
                
                # Combine all masks
                combined_mask = np.zeros((masks.shape[1], masks.shape[2]), dtype=np.uint8)
                for mask in masks:
                    combined_mask = np.logical_or(combined_mask, mask).astype(np.uint8)
                
                # Resize combined_mask to original image size
                if combined_mask.shape != (H, W):
                    combined_mask = cv2.resize(combined_mask, (W, H), interpolation=cv2.INTER_NEAREST)
                
                # Dilate mask slightly for safer coverage
                kernel = np.ones((5, 5), np.uint8)
                combined_mask = cv2.dilate(combined_mask, kernel, iterations=2)
                    
                # Blur entire image heavily
                blurred_img = cv2.GaussianBlur(img, (99, 99), 50)
                
                # Composite
                out = img.copy()
                mask_3d = np.repeat(combined_mask[:, :, np.newaxis], 3, axis=2)
                out = np.where(mask_3d > 0, blurred_img, out)
                return out
        except Exception as e:
            import logging
            logger = logging.getLogger("privacy_guardian")
            logger.error(f"FastSAM error: {e}")
            
        # Fallback to box blur
        return self.apply_gaussian_blur(img, boxes_01)
