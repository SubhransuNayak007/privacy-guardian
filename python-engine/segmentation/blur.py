import cv2
import numpy as np

def apply_gaussian_blur(img: np.ndarray, boxes_01: list) -> np.ndarray:
    H, W = img.shape[:2]
    out = img.copy()
    for bx in boxes_01:
        x1, y1, x2, y2 = int(bx[0]*W), int(bx[1]*H), int(bx[2]*W), int(bx[3]*H)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(W, x2), min(H, y2)
        if x2 <= x1 or y2 <= y1:
            continue
        roi = out[y1:y2, x1:x2]
        h_roi, w_roi = roi.shape[:2]
        if h_roi == 0 or w_roi == 0:
            continue
            
        # Dynamically calculate kernel size based on ROI size, max 51
        kw = min(51, w_roi if w_roi % 2 != 0 else w_roi - 1)
        kh = min(51, h_roi if h_roi % 2 != 0 else h_roi - 1)
        kw, kh = max(3, kw), max(3, kh)
        
        roi = cv2.GaussianBlur(roi, (kw, kh), 0)
        out[y1:y2, x1:x2] = roi
    return out
