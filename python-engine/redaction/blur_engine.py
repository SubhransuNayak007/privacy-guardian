"""
Blurring engine for redacting sensitive regions in images.
"""

import cv2
import numpy as np

class AdaptiveBlur:
    """
    Applies adaptive blurring techniques to image regions based on the
    type of sensitive information detected.
    """
    
    def apply(self, image: np.ndarray, bbox: tuple, label: str) -> np.ndarray:
        """
        Applies blur to a specific bounding box in the image, with intensity
        adaptive to the label type.
        
        Args:
            image (np.ndarray): The original image.
            bbox (tuple): Bounding box in the format (x1, y1, x2, y2).
            label (str): The label of the detected object (e.g., 'FACE', 'TEXT').
            
        Returns:
            np.ndarray: The image with the redacted region.
        """
        # Ensure bbox is within image bounds
        h, w = image.shape[:2]
        x1, y1, x2, y2 = bbox
        
        x1 = max(0, int(x1))
        y1 = max(0, int(y1))
        x2 = min(w, int(x2))
        y2 = min(h, int(y2))
        
        if x1 >= x2 or y1 >= y2:
            return image # Invalid bounding box
            
        redacted_image = image.copy()
        roi = redacted_image[y1:y2, x1:x2]
        
        if label.upper() == 'FACE':
            # Large Gaussian blur for faces
            ksize = 33 # roughly 32px radius context, must be odd
            roi = cv2.GaussianBlur(roi, (ksize, ksize), sigmaX=30, sigmaY=30)
        else:
            # Assume 'TEXT' or document field, use smaller radius
            ksize = 19 # roughly 18px radius context, must be odd
            roi = cv2.GaussianBlur(roi, (ksize, ksize), sigmaX=15, sigmaY=15)
            
        redacted_image[y1:y2, x1:x2] = roi
        return redacted_image
