import cv2
import numpy as np
import io
from PIL import Image

def strip_exif(img_data: bytes) -> bytes:
    try:
        image = Image.open(io.BytesIO(img_data))
        data = list(image.getdata())
        image_without_exif = Image.new(image.mode, image.size)
        image_without_exif.putdata(data)
        out = io.BytesIO()
        image_without_exif.save(out, format="JPEG")
        return out.getvalue()
    except Exception:
        return img_data

def check_image_quality(img: np.ndarray) -> bool:
    # Check if too dark or too blurry
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur_val = cv2.Laplacian(gray, cv2.CV_64F).var()
    if blur_val < 10.0:  # arbitrary threshold
        return False
    return True

def enhance_image(img: np.ndarray) -> np.ndarray:
    # CLAHE
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return cv2.cvtColor(clahe.apply(gray), cv2.COLOR_GRAY2BGR)
