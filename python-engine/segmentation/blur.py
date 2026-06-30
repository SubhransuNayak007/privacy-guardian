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
        roi = cv2.GaussianBlur(roi, (51, 51), 30)
        out[y1:y2, x1:x2] = roi
    return out
