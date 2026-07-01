from typing import List, Dict, Any
import cv2

def detect_barcodes_and_qr(img) -> List[Dict[str, Any]]:
    dets = []
    try:
        from pyzbar.pyzbar import decode
        decoded_objects = decode(img)
        for obj in decoded_objects:
            # Check obj type
            lbl = "qr_code" if obj.type == "QRCODE" else "barcode"
            
            # Get bounding box
            rect = obj.rect
            # rect is Rect(left, top, width, height)
            if rect:
                x1, y1 = rect.left, rect.top
                x2, y2 = x1 + rect.width, y1 + rect.height
                dets.append({
                    "box": [float(x1), float(y1), float(x2), float(y2)],
                    "score": 0.99,
                    "label": lbl,
                    "text": obj.data.decode("utf-8") if obj.data else ""
                })
    except Exception as e:
        print(f"Barcode detection error: {e}")
    return dets
