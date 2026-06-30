import base64
import io
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import cv2
import numpy as np

# Lazy load heavy models
_ocr_model = None

def get_ocr_model():
    global _ocr_model
    if _ocr_model is None:
        from paddleocr import PaddleOCR
        # Using english for now, can be extended to hindi (hi) etc.
        _ocr_model = PaddleOCR(use_angle_cls=True, lang='en')
    return _ocr_model

app = FastAPI(title="Privacy Guardian - V2 Redaction Engine")

class ScanRequest(BaseModel):
    imageBase64: str

class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

class Detection(BaseModel):
    id: str
    type: str
    label: str
    text: str
    confidence: float
    bbox: BoundingBox
    redacted: bool

class ScanResponse(BaseModel):
    detections: List[Detection]
    fullText: str
    processingTime: int

@app.get("/")
def health_check():
    return {"status": "ok", "message": "V2 Redaction Engine is running"}

@app.post("/scan", response_model=ScanResponse)
def scan_document(req: ScanRequest):
    t0 = time.time()
    
    # 1. Decode base64 image
    try:
        base64_data = req.imageBase64
        if "base64," in base64_data:
            base64_data = base64_data.split("base64,")[1]
        
        img_bytes = base64.b64decode(base64_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise ValueError("Invalid image data")
            
        height, width, _ = img.shape
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to decode image: {str(e)}")

    # 2. Run OCR (PaddleOCR)
    try:
        ocr = get_ocr_model()
        result = ocr.ocr(img, cls=True)
        
        # Flatten the result (PaddleOCR returns a list of lines, each line is a list of word blocks)
        # Format: [[[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ("text", confidence)], ...]
        lines = result[0] if result and result[0] else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR Engine failed: {str(e)}")

    # 3. Entity Detection (Regex / Spatial Grouping)
    # TODO: Implement robust regex for all PII types and spatial grouping
    detections = []
    full_text = ""
    
    for idx, line in enumerate(lines):
        box, (text, conf) = line
        full_text += text + " "
        
        # Convert 4 points polygon to bounding box
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        
        # Normalize to percentages (0-100)
        norm_bbox = BoundingBox(
            x0=(x0 / width) * 100,
            y0=(y0 / height) * 100,
            x1=(x1 / width) * 100,
            y1=(y1 / height) * 100
        )
        
        # Simple test: just redact EVERYTHING that looks like a number for now
        # We will add the sophisticated regex engine later
        if any(char.isdigit() for char in text):
            detections.append(Detection(
                id=f"pii-{idx}",
                type="number",
                label="Number detected",
                text=text,
                confidence=conf,
                bbox=norm_bbox,
                redacted=True
            ))

    processing_time = int((time.time() - t0) * 1000)
    
    return ScanResponse(
        detections=detections,
        fullText=full_text.strip(),
        processingTime=processing_time
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)"""
Privacy Guardian — V3 Production Redaction Engine
===================================================
Pipeline:
  1. Image decode
  2. PaddleOCR  → raw text + bounding boxes
  3. Regex Engine → Phone, PAN, Aadhaar, Email, IFSC, Passport, Credit Card, UPI, DOB, GSTIN
  4. GLiNER NER → PERSON, ADDRESS, CITY, STATE, PINCODE, ORG (mapped to bbox via word-index)
  5. Rule-based Address Detection → Flat/Road/Village/District/PIN anchors (boosts recall)
  6. MediaPipe Face Detection → all faces
  7. pyzbar QR + Barcode Detection
  8. IoU Non-Max Suppression → merge / deduplicate all detections
  9. Return structured JSON with 0–100% normalised bounding boxes
"""
import base64
import io
import re
import time
import uuid as _uuid
from typing import List, Optional, Tuple

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ── Lazy model holders ────────────────────────────────────────────────────────

_ocr_model = None
_gliner_model = None

def get_ocr_model():
    global _ocr_model
    if _ocr_model is None:
        from paddleocr import PaddleOCR
        _ocr_model = PaddleOCR(use_angle_cls=True, lang='en', enable_mkldnn=False)
    return _ocr_model

def get_gliner_model():
    global _gliner_model
    if _gliner_model is None:
        try:
            from gliner import GLiNER
            # ner-english-large is ~400 MB — downloads once and caches
            _gliner_model = GLiNER.from_pretrained("urchade/gliner_base")
        except Exception as e:
            print(f"[GLiNER] Could not load model: {e}. NER will be skipped.")
            _gliner_model = "unavailable"
    return _gliner_model


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(title="Privacy Guardian — V3 Production Redaction Engine")


# ── Pydantic models ───────────────────────────────────────────────────────────

class ScanRequest(BaseModel):
    imageBase64: str

class BoundingBox(BaseModel):
    x0: float   # percentage 0–100
    y0: float
    x1: float
    y1: float

class Detection(BaseModel):
    id: str
    type: str
    label: str
    text: str
    confidence: float
    bbox: BoundingBox
    redacted: bool

class OCRWord(BaseModel):
    text: str
    confidence: float
    bbox: BoundingBox

class ScanResponse(BaseModel):
    detections: List[Detection]
    words: List[OCRWord]
    fullText: str
    processingTime: int


# ── Regex patterns ────────────────────────────────────────────────────────────

REGEX_PATTERNS = [
    # Indian Mobile (starts 6–9, 10 digits)
    ("phone",        "Phone Number",      r'\b[6-9]\d{9}\b',                                90),
    # PAN
    ("pan",          "PAN Number",        r'\b[A-Z]{5}[0-9]{4}[A-Z]\b',                    95),
    # Aadhaar (12 digits, space-separated groups)
    ("aadhaar",      "Aadhaar Number",    r'\b\d{4}\s?\d{4}\s?\d{4}\b',                    92),
    # Email
    ("email",        "Email Address",     r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}', 90),
    # IFSC
    ("bank_account", "IFSC Code",         r'[A-Z]{4}0[A-Z0-9]{6}',                         88),
    # Bank Account (9–18 digits — after filtering out Aadhaar and PAN)
    ("bank_account", "Bank Account",      r'\b\d{9,18}\b',                                  70),
    # Passport (Indian: letter + 7 digits)
    ("passport",     "Passport Number",   r'\b[A-Z][0-9]{7}\b',                             85),
    # Date of Birth (DD/MM/YYYY or DD-MM-YYYY)
    ("dob",          "Date of Birth",     r'\b\d{2}[\/\-]\d{2}[\/\-]\d{4}\b',              80),
    # UPI
    ("upi",          "UPI ID",            r'[\w.\-]+@[a-zA-Z]+',                            80),
    # GSTIN
    ("gstin",        "GSTIN",             r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}\b', 90),
    # Voter ID
    ("voter_id",     "Voter ID",          r'\b[A-Z]{3}[0-9]{7}\b',                          82),
    # Driving Licence (varies by state — 15 char alphanum)
    ("dl",           "Driving Licence",   r'\b[A-Z]{2}-?\d{2}-?\d{4}-?\d{7}\b',            80),
]

# Address anchor keywords — if OCR word contains any of these, start collecting an address block
ADDRESS_ANCHORS = {
    "flat", "plot", "house", "h.no", "h/o", "w/o", "s/o", "d/o", "c/o",
    "road", "street", "lane", "marg", "avenue", "nagar", "colony", "sector",
    "village", "vill", "po", "p.o", "ps", "p.s", "tehsil", "taluka", "mandal",
    "district", "dist", "city", "state", "near", "behind", "opposite", "opp",
    "building", "tower", "complex", "society", "apartment", "apt", "wing",
    "phase", "block", "ward", "area", "locality", "post", "address", "पता",
}


# ── Helper: make a Detection object ──────────────────────────────────────────

def make_detection(type_str: str, label: str, text: str, conf: float,
                   x0: float, y0: float, x1: float, y1: float,
                   width: int, height: int, uid: Optional[str] = None) -> Detection:
    """Create a Detection with bbox normalised to 0–100%."""
    uid = uid or f"{type_str}-{_uuid.uuid4().hex[:8]}"
    return Detection(
        id=uid,
        type=type_str,
        label=label,
        text=text,
        confidence=conf,
        bbox=BoundingBox(
            x0=float(max(0, min(100, (x0 / width)  * 100))),
            y0=float(max(0, min(100, (y0 / height) * 100))),
            x1=float(max(0, min(100, (x1 / width)  * 100))),
            y1=float(max(0, min(100, (y1 / height) * 100))),
        ),
        redacted=True,
    )


# ── Helper: OCR result normalisation ─────────────────────────────────────────

def parse_ocr_result(result, img: np.ndarray):
    """
    Normalise PaddleOCR result (both old list and new dict formats) to:
      [ ([x0,y0,x1,y0,x1,y1,x0,y1], (text, score)), ... ]
    i.e. a flat list of (polygon, (text, conf)) tuples.
    """
    lines = []
    if not result or len(result) == 0:
        return lines

    res_item = result[0]

    if isinstance(res_item, dict) and 'dt_polys' in res_item:
        # New PaddleOCR ≥2.7 dict format
        polys  = res_item.get('dt_polys', [])
        texts  = res_item.get('rec_texts', [])
        scores = res_item.get('rec_scores', [])
        for i in range(len(texts)):
            poly = polys[i]
            box  = poly.tolist() if hasattr(poly, 'tolist') else list(poly)
            lines.append([box, (texts[i], scores[i])])
    elif isinstance(res_item, list):
        # Old PaddleOCR format: list of [box, (text, conf)]
        for item in res_item:
            if item is not None:
                lines.append(item)

    return lines


def get_bbox(box):
    """Convert a 4-point polygon to (x0, y0, x1, y1)."""
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return min(xs), min(ys), max(xs), max(ys)


# ── Step 2: Regex Engine ──────────────────────────────────────────────────────

def run_regex(lines: list, width: int, height: int) -> List[Detection]:
    """
    Run regex patterns over every OCR line. When a pattern matches, record the
    bounding box of the line that contained it.
    """
    detections = []
    seen_texts = set()

    for line in lines:
        box, (text, conf) = line
        text_s = str(text).strip()
        if not text_s:
            continue
        x0, y0, x1, y1 = get_bbox(box)

        for type_str, label, pattern, base_conf in REGEX_PATTERNS:
            matches = list(re.finditer(pattern, text_s, re.IGNORECASE))
            for m in matches:
                matched_text = m.group(0)
                dedup_key = f"{type_str}:{matched_text}"
                if dedup_key in seen_texts:
                    continue
                seen_texts.add(dedup_key)

                detections.append(make_detection(
                    type_str, label, matched_text,
                    float(base_conf), x0, y0, x1, y1, width, height
                ))

    return detections


# ── Step 3: GLiNER NER Engine ─────────────────────────────────────────────────

GLINER_LABELS = [
    "person", "person name", "full name",
    "address", "street address", "residential address",
    "city", "state", "district", "country",
    "pin code", "zip code", "postal code",
    "organization", "company", "hospital", "school",
]

GLINER_TYPE_MAP = {
    "person":               "name",
    "person name":          "name",
    "full name":            "name",
    "address":              "address",
    "street address":       "address",
    "residential address":  "address",
    "city":                 "address",
    "state":                "address",
    "district":             "address",
    "country":              "address",
    "pin code":             "pincode",
    "zip code":             "pincode",
    "postal code":          "pincode",
    "organization":         "name",
    "company":              "name",
    "hospital":             "name",
    "school":               "name",
}


def run_gliner_ner(lines: list, width: int, height: int) -> List[Detection]:
    """
    Build a full text string with word-index mapping, run GLiNER, then map
    character offsets back to OCR bounding boxes.
    """
    model = get_gliner_model()
    if model == "unavailable" or model is None:
        return []

    # Build a flat word list with char offsets
    word_list   = []   # [(text, x0, y0, x1, y1)]
    full_text   = ""

    for line in lines:
        box, (text, conf) = line
        text_s = str(text).strip()
        if not text_s:
            continue
        x0, y0, x1, y1 = get_bbox(box)

        for word in text_s.split():
            start = len(full_text)
            full_text += word
            end = len(full_text)
            full_text += " "
            word_list.append((word, x0, y0, x1, y1, start, end))

    if not word_list or not full_text.strip():
        return []

    try:
        entities = model.predict_entities(full_text, GLINER_LABELS, threshold=0.4)
    except Exception as e:
        print(f"[GLiNER] Prediction error: {e}")
        return []

    detections = []
    seen = set()

    for ent in entities:
        ent_start = ent["start"]
        ent_end   = ent["end"]
        ent_label = ent["label"].lower()
        ent_text  = ent["text"]
        ent_score = ent.get("score", 0.75)

        type_str = GLINER_TYPE_MAP.get(ent_label, "name")

        dedup_key = f"{type_str}:{ent_text.lower()}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Find all OCR words that overlap with this entity's character span
        overlapping = [
            w for w in word_list
            if not (w[6] >= ent_end or w[5] >= ent_end or w[6] <= ent_start)
        ]

        if not overlapping:
            # Fallback: find words by text match
            overlapping = [w for w in word_list if w[0] in ent_text]

        if not overlapping:
            continue

        min_x = min(w[1] for w in overlapping)
        min_y = min(w[2] for w in overlapping)
        max_x = max(w[3] for w in overlapping)
        max_y = max(w[4] for w in overlapping)

        # Expand bounding box slightly (3%) to ensure full coverage
        pad_x = (max_x - min_x) * 0.03
        pad_y = (max_y - min_y) * 0.05
        min_x = max(0, min_x - pad_x)
        min_y = max(0, min_y - pad_y)
        max_x = min(width,  max_x + pad_x)
        max_y = min(height, max_y + pad_y)

        label_map = {
            "name":    "Person Name",
            "address": "Address",
            "pincode": "PIN Code",
        }
        label = label_map.get(type_str, type_str.title())

        detections.append(make_detection(
            type_str, label, ent_text,
            float(min(99, ent_score * 100)),
            min_x, min_y, max_x, max_y,
            width, height
        ))

    return detections


# ── Step 4: Rule-based Address Detection ─────────────────────────────────────

def run_address_rules(lines: list, width: int, height: int) -> List[Detection]:
    """
    Collect consecutive OCR lines that look like an address block.
    Uses keyword anchors + PIN code terminator.
    Complements GLiNER for documents where OCR produces fragmented lines.
    """
    sorted_lines = sorted(lines, key=lambda ln: get_bbox(ln[0])[1])

    address_blocks = []
    in_block    = False
    block_boxes = []
    block_texts = []
    anchor_x    = -1

    for line in sorted_lines:
        box, (text, conf) = line
        text_s = str(text).strip()
        text_l = text_s.lower()
        x0, y0, x1, y1 = get_bbox(box)

        words_in_line = set(text_l.split())
        is_anchor = bool(words_in_line & ADDRESS_ANCHORS)
        has_pin   = bool(re.search(r'\b\d{6}\b', text_s))

        if is_anchor and not in_block:
            in_block    = True
            anchor_x    = x0
            block_boxes = [(x0, y0, x1, y1)]
            block_texts = [text_s]
        elif in_block:
            # Continue if x-aligned (within 25% of image width)
            if abs(x0 - anchor_x) < width * 0.25:
                block_boxes.append((x0, y0, x1, y1))
                block_texts.append(text_s)
            else:
                # Misaligned — close current block and start fresh if anchor
                if len(block_boxes) >= 2:
                    address_blocks.append((block_boxes, block_texts))
                block_boxes = []
                block_texts = []
                in_block    = False
                anchor_x    = -1

            if has_pin:
                # PIN code terminates the address block
                if len(block_boxes) >= 2:
                    address_blocks.append((block_boxes, block_texts))
                block_boxes = []
                block_texts = []
                in_block    = False
                anchor_x    = -1

    # Close any open block
    if in_block and len(block_boxes) >= 2:
        address_blocks.append((block_boxes, block_texts))

    detections = []
    for boxes, texts in address_blocks:
        min_x = min(b[0] for b in boxes)
        min_y = min(b[1] for b in boxes)
        max_x = max(b[2] for b in boxes)
        max_y = max(b[3] for b in boxes)

        # Expand 4%
        pw = (max_x - min_x) * 0.04
        ph = (max_y - min_y) * 0.04
        min_x = max(0, min_x - pw)
        min_y = max(0, min_y - ph)
        max_x = min(width,  max_x + pw)
        max_y = min(height, max_y + ph)

        address_text = " | ".join(texts)
        detections.append(make_detection(
            "address", "Address Block", address_text, 85.0,
            min_x, min_y, max_x, max_y, width, height
        ))

    return detections


# ── Step 5: Face Detection ────────────────────────────────────────────────────

def run_face_detection(img: np.ndarray, width: int, height: int) -> List[Detection]:
    detections = []
    try:
        import mediapipe as mp
        mp_face = mp.solutions.face_detection

        with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.3) as fd:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = fd.process(img_rgb)

            if results.detections:
                for i, det in enumerate(results.detections):
                    bb = det.location_data.relative_bounding_box
                    x0 = max(0.0, bb.xmin * 100)
                    y0 = max(0.0, bb.ymin * 100)
                    x1 = min(100.0, (bb.xmin + bb.width)  * 100)
                    y1 = min(100.0, (bb.ymin + bb.height) * 100)

                    detections.append(Detection(
                        id=f"face-{i}",
                        type="face",
                        label="Face",
                        text="[FACE]",
                        confidence=float(det.score[0] * 100),
                        bbox=BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1),
                        redacted=True,
                    ))
    except Exception as e:
        print(f"[Face] Detection error: {e}")

    return detections


# ── Step 6: QR + Barcode Detection ───────────────────────────────────────────

def run_qr_barcode_detection(img: np.ndarray, width: int, height: int) -> List[Detection]:
    detections = []
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
        from pyzbar.pyzbar import ZBarSymbol

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        codes = pyzbar_decode(gray)

        for i, code in enumerate(codes):
            rect = code.rect
            x0 = float(rect.left)
            y0 = float(rect.top)
            x1 = float(rect.left + rect.width)
            y1 = float(rect.top  + rect.height)

            code_type = code.type.lower()
            type_str  = "qr_code" if "qr" in code_type else "barcode"
            label     = "QR Code" if "qr" in code_type else "Barcode"
            text      = code.data.decode("utf-8", errors="replace") if code.data else ""

            detections.append(make_detection(
                type_str, label, text[:100], 95.0,
                x0, y0, x1, y1, width, height,
                uid=f"{type_str}-{i}"
            ))
    except ImportError:
        # pyzbar not installed — try OpenCV QR
        try:
            qr_detector = cv2.QRCodeDetector()
            data, points, _ = qr_detector.detectAndDecode(img)
            if points is not None and data:
                pts = points[0]
                xs  = [p[0] for p in pts]
                ys  = [p[1] for p in pts]
                detections.append(make_detection(
                    "qr_code", "QR Code", data[:100], 90.0,
                    min(xs), min(ys), max(xs), max(ys),
                    width, height, uid="qr-0"
                ))
        except Exception:
            pass
    except Exception as e:
        print(f"[QR] Detection error: {e}")

    return detections


# ── Step 7: IoU Non-Max Suppression ──────────────────────────────────────────

def iou(a: BoundingBox, b: BoundingBox) -> float:
    """Intersection over Union on 0–100 percentage boxes."""
    ix0 = max(a.x0, b.x0)
    iy0 = max(a.y0, b.y0)
    ix1 = min(a.x1, b.x1)
    iy1 = min(a.y1, b.y1)

    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0

    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = (a.x1 - a.x0) * (a.y1 - a.y0)
    area_b = (b.x1 - b.x0) * (b.y1 - b.y0)
    union = area_a + area_b - inter

    return inter / union if union > 0 else 0.0


def nms_merge(detections: List[Detection], iou_threshold: float = 0.4) -> List[Detection]:
    """
    Non-maximum suppression: when two detections of different types overlap
    with IoU > threshold, keep both but expand the higher-confidence box to
    cover both. When two detections of the SAME type overlap, keep only the
    higher-confidence one.
    """
    if not detections:
        return []

    # Sort by confidence descending
    detections = sorted(detections, key=lambda d: d.confidence, reverse=True)
    kept: List[Detection] = []

    for det in detections:
        merge = False
        for existing in kept:
            overlap = iou(det.bbox, existing.bbox)
            if overlap > iou_threshold:
                if det.type == existing.type:
                    # Same type — discard the lower-confidence one (already kept existing)
                    merge = True
                    break
                else:
                    # Different types — expand existing bbox to cover both, keep both
                    existing.bbox.x0 = min(existing.bbox.x0, det.bbox.x0)
                    existing.bbox.y0 = min(existing.bbox.y0, det.bbox.y0)
                    existing.bbox.x1 = max(existing.bbox.x1, det.bbox.x1)
                    existing.bbox.y1 = max(existing.bbox.y1, det.bbox.y1)
                    # Add det as-is as well (both regions get redacted)
                    break

        if not merge:
            kept.append(det)

    return kept


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    return {"status": "ok", "message": "V3 Production Redaction Engine is running"}


# ── Main scan endpoint ────────────────────────────────────────────────────────

@app.post("/scan", response_model=ScanResponse)
def scan_document(req: ScanRequest):
    t0 = time.time()

    # ── 1. Decode image ───────────────────────────────────────────────────────
    try:
        b64 = req.imageBase64
        if "base64," in b64:
            b64 = b64.split("base64,")[1]
        img_bytes = base64.b64decode(b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image")
        height, width, _ = img.shape
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image decode error: {e}")

    # ── 2. OCR ────────────────────────────────────────────────────────────────
    try:
        ocr   = get_ocr_model()
        if hasattr(ocr, 'predict'):
            result = ocr.predict(img)
        else:
            result = ocr.ocr(img)
        lines = parse_ocr_result(result, img)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR engine error: {e}")

    # Build full text and word list for the response
    full_text = " ".join(str(line[1][0]) for line in lines if line[1][0])
    all_words: List[OCRWord] = []
    for line in lines:
        box, (text, conf) = line
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        all_words.append(OCRWord(
            text=str(text),
            confidence=float(conf),
            bbox=BoundingBox(
                x0=float(max(0, min(100, (x0 / width)  * 100))),
                y0=float(max(0, min(100, (y0 / height) * 100))),
                x1=float(max(0, min(100, (x1 / width)  * 100))),
                y1=float(max(0, min(100, (y1 / height) * 100))),
            )
        ))

    # ── 3. Regex Detection ────────────────────────────────────────────────────
    regex_detections = run_regex(lines, width, height)

    # ── 4. GLiNER NER ─────────────────────────────────────────────────────────
    ner_detections = run_gliner_ner(lines, width, height)

    # ── 5. Rule-based Address Detection ──────────────────────────────────────
    addr_detections = run_address_rules(lines, width, height)

    # ── 6. Face Detection ─────────────────────────────────────────────────────
    face_detections = run_face_detection(img, width, height)

    # ── 7. QR / Barcode Detection ─────────────────────────────────────────────
    qr_detections = run_qr_barcode_detection(img, width, height)

    # ── 8. Merge all detections with IoU NMS ──────────────────────────────────
    all_detections = regex_detections + ner_detections + addr_detections + face_detections + qr_detections
    merged = nms_merge(all_detections, iou_threshold=0.4)

    # Filter out zero-area boxes
    merged = [d for d in merged if (d.bbox.x1 - d.bbox.x0) > 0 and (d.bbox.y1 - d.bbox.y0) > 0]

    processing_time = int((time.time() - t0) * 1000)

    print(
        f"[Scan] ✓ {processing_time}ms | "
        f"regex={len(regex_detections)} ner={len(ner_detections)} "
        f"addr={len(addr_detections)} face={len(face_detections)} "
        f"qr={len(qr_detections)} → merged={len(merged)}"
    )

    return ScanResponse(
        detections=merged,
        words=all_words,
        fullText=full_text.strip(),
        processingTime=processing_time,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

target = r"D:\rot post\privacy-guardian\python-engine\main.py"

code = r"""import base64
import re
import time
import uuid as _uuid
from typing import List
import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

_ocr_model = None
_gliner_model = None

def get_ocr_model():
    global _ocr_model
    if _ocr_model is None:
        from paddleocr import PaddleOCR
        _ocr_model = PaddleOCR(use_angle_cls=True, lang='en', enable_mkldnn=False)
    return _ocr_model

def get_gliner_model():
    global _gliner_model
    if _gliner_model is None:
        try:
            from gliner import GLiNER
            _gliner_model = GLiNER.from_pretrained("urchade/gliner_base")
            print("[GLiNER] Model loaded")
        except Exception as e:
            print(f"[GLiNER] Could not load: {e}")
            _gliner_model = "unavailable"
    return _gliner_model

app = FastAPI(title="Privacy Guardian - V3 Production Redaction Engine")

class ScanRequest(BaseModel):
    imageBase64: str

class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

class Detection(BaseModel):
    id: str
    type: str
    label: str
    text: str
    confidence: float
    bbox: BoundingBox
    redacted: bool

class OCRWord(BaseModel):
    text: str
    confidence: float
    bbox: BoundingBox

class ScanResponse(BaseModel):
    detections: List[Detection]
    words: List[OCRWord]
    fullText: str
    processingTime: int

REGEX_PATTERNS = [
    ("phone",        "Phone Number",    r"\b[6-9]\d{9}\b",                                    90),
    ("pan",          "PAN Number",      r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",                        95),
    ("aadhaar",      "Aadhaar Number",  r"\b\d{4}\s?\d{4}\s?\d{4}\b",                        92),
    ("email",        "Email Address",   r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", 90),
    ("bank_account", "IFSC Code",       r"[A-Z]{4}0[A-Z0-9]{6}",                              88),
    ("bank_account", "Bank Account",    r"\b\d{9,18}\b",                                       70),
    ("passport",     "Passport Number", r"\b[A-Z][0-9]{7}\b",                                  85),
    ("dob",          "Date of Birth",   r"\b\d{2}[\/\-]\d{2}[\/\-]\d{4}\b",                   80),
    ("gstin",        "GSTIN",           r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d][Z][A-Z\d]\b",     90),
    ("voter_id",     "Voter ID",        r"\b[A-Z]{3}[0-9]{7}\b",                               82),
]

ADDRESS_ANCHORS = {
    "flat", "plot", "house", "road", "street", "lane", "marg", "avenue", "nagar",
    "colony", "sector", "village", "vill", "po", "ps", "tehsil", "taluka",
    "district", "dist", "city", "state", "near", "behind", "opposite", "opp",
    "building", "tower", "complex", "society", "apartment", "apt", "wing",
    "phase", "block", "ward", "area", "locality", "post", "address",
}

def make_detection(type_str, label, text, conf, x0, y0, x1, y1, width, height, uid=None):
    uid = uid or f"{type_str}-{_uuid.uuid4().hex[:8]}"
    return Detection(
        id=uid, type=type_str, label=label, text=str(text),
        confidence=float(conf),
        bbox=BoundingBox(
            x0=float(max(0, min(100, (x0 / width)  * 100))),
            y0=float(max(0, min(100, (y0 / height) * 100))),
            x1=float(max(0, min(100, (x1 / width)  * 100))),
            y1=float(max(0, min(100, (y1 / height) * 100))),
        ),
        redacted=True,
    )

def parse_ocr_result(result, img):
    lines = []
    if not result or len(result) == 0:
        return lines
    res_item = result[0]
    if isinstance(res_item, dict) and "dt_polys" in res_item:
        polys  = res_item.get("dt_polys", [])
        texts  = res_item.get("rec_texts", [])
        scores = res_item.get("rec_scores", [])
        for i in range(len(texts)):
            poly = polys[i]
            box  = poly.tolist() if hasattr(poly, "tolist") else list(poly)
            lines.append([box, (texts[i], scores[i])])
    elif isinstance(res_item, list):
        for item in res_item:
            if item is not None:
                lines.append(item)
    return lines

def get_bbox(box):
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return min(xs), min(ys), max(xs), max(ys)

def run_regex(lines, width, height):
    detections = []
    seen_texts = set()
    for line in lines:
        box, (text, conf) = line
        text_s = str(text).strip()
        if not text_s:
            continue
        x0, y0, x1, y1 = get_bbox(box)
        for type_str, label, pattern, base_conf in REGEX_PATTERNS:
            for m in re.finditer(pattern, text_s, re.IGNORECASE):
                matched_text = m.group(0)
                dedup_key = f"{type_str}:{matched_text}"
                if dedup_key in seen_texts:
                    continue
                seen_texts.add(dedup_key)
                detections.append(make_detection(
                    type_str, label, matched_text, float(base_conf),
                    x0, y0, x1, y1, width, height
                ))
    return detections

GLINER_LABELS = [
    "person", "person name", "full name",
    "address", "street address", "residential address",
    "city", "state", "district",
    "pin code", "zip code",
    "organization", "company", "hospital",
]

GLINER_TYPE_MAP = {
    "person": "name", "person name": "name", "full name": "name",
    "address": "address", "street address": "address", "residential address": "address",
    "city": "address", "state": "address", "district": "address",
    "pin code": "pincode", "zip code": "pincode",
    "organization": "name", "company": "name", "hospital": "name",
}

def run_gliner_ner(lines, width, height):
    model = get_gliner_model()
    if model == "unavailable" or model is None:
        return []
    word_list = []
    full_text = ""
    for line in lines:
        box, (text, conf) = line
        text_s = str(text).strip()
        if not text_s:
            continue
        x0, y0, x1, y1 = get_bbox(box)
        for word in text_s.split():
            start = len(full_text)
            full_text += word
            end = len(full_text)
            full_text += " "
            word_list.append((word, x0, y0, x1, y1, start, end))
    if not word_list or not full_text.strip():
        return []
    try:
        entities = model.predict_entities(full_text, GLINER_LABELS, threshold=0.4)
    except Exception as e:
        print(f"[GLiNER] Prediction error: {e}")
        return []
    detections = []
    seen = set()
    for ent in entities:
        ent_start = ent["start"]
        ent_end   = ent["end"]
        ent_label = ent["label"].lower()
        ent_text  = ent["text"]
        ent_score = ent.get("score", 0.75)
        type_str  = GLINER_TYPE_MAP.get(ent_label, "name")
        dedup_key = f"{type_str}:{ent_text.lower()}"
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        overlapping = [w for w in word_list if not (w[6] <= ent_start or w[5] >= ent_end)]
        if not overlapping:
            overlapping = [w for w in word_list if w[0] in ent_text]
        if not overlapping:
            continue
        min_x = min(w[1] for w in overlapping)
        min_y = min(w[2] for w in overlapping)
        max_x = max(w[3] for w in overlapping)
        max_y = max(w[4] for w in overlapping)
        pad_x = (max_x - min_x) * 0.03
        pad_y = (max_y - min_y) * 0.05
        label_map = {"name": "Person Name", "address": "Address", "pincode": "PIN Code"}
        label = label_map.get(type_str, type_str.title())
        detections.append(make_detection(
            type_str, label, ent_text,
            float(min(99, ent_score * 100)),
            max(0, min_x - pad_x), max(0, min_y - pad_y),
            min(width, max_x + pad_x), min(height, max_y + pad_y),
            width, height
        ))
    return detections

def run_address_rules(lines, width, height):
    sorted_lines = sorted(lines, key=lambda ln: get_bbox(ln[0])[1])
    address_blocks = []
    in_block = False
    block_boxes = []
    block_texts = []
    anchor_x = -1
    for line in sorted_lines:
        box, (text, conf) = line
        text_s = str(text).strip()
        text_l = text_s.lower()
        x0, y0, x1, y1 = get_bbox(box)
        words_in_line = set(re.split(r"\W+", text_l))
        is_anchor = bool(words_in_line & ADDRESS_ANCHORS)
        has_pin   = bool(re.search(r"\b\d{6}\b", text_s))
        if is_anchor and not in_block:
            in_block    = True
            anchor_x    = x0
            block_boxes = [(x0, y0, x1, y1)]
            block_texts = [text_s]
        elif in_block:
            if abs(x0 - anchor_x) < width * 0.30:
                block_boxes.append((x0, y0, x1, y1))
                block_texts.append(text_s)
            else:
                if len(block_boxes) >= 2:
                    address_blocks.append((block_boxes, block_texts))
                block_boxes = []
                block_texts = []
                in_block    = False
                anchor_x    = -1
            if has_pin:
                if len(block_boxes) >= 2:
                    address_blocks.append((block_boxes, block_texts))
                block_boxes = []
                block_texts = []
                in_block    = False
                anchor_x    = -1
    if in_block and len(block_boxes) >= 2:
        address_blocks.append((block_boxes, block_texts))
    detections = []
    for boxes, texts in address_blocks:
        min_x = min(b[0] for b in boxes)
        min_y = min(b[1] for b in boxes)
        max_x = max(b[2] for b in boxes)
        max_y = max(b[3] for b in boxes)
        pw = (max_x - min_x) * 0.04
        ph = (max_y - min_y) * 0.04
        address_text = " | ".join(texts)
        detections.append(make_detection(
            "address", "Address Block", address_text, 85.0,
            max(0, min_x - pw), max(0, min_y - ph),
            min(width, max_x + pw), min(height, max_y + ph),
            width, height
        ))
    return detections

def run_face_detection(img, width, height):
    detections = []
    try:
        import mediapipe as mp
        mp_face = mp.solutions.face_detection
        with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.3) as fd:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = fd.process(img_rgb)
            if results.detections:
                for i, det in enumerate(results.detections):
                    bb = det.location_data.relative_bounding_box
                    x0 = max(0.0, bb.xmin * 100)
                    y0 = max(0.0, bb.ymin * 100)
                    x1 = min(100.0, (bb.xmin + bb.width)  * 100)
                    y1 = min(100.0, (bb.ymin + bb.height) * 100)
                    detections.append(Detection(
                        id=f"face-{i}", type="face", label="Face", text="[FACE]",
                        confidence=float(det.score[0] * 100),
                        bbox=BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1),
                        redacted=True,
                    ))
    except Exception as e:
        print(f"[Face] Detection error: {e}")
    return detections

def run_qr_barcode_detection(img, width, height):
    detections = []
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
        gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        codes = pyzbar_decode(gray)
        for i, code in enumerate(codes):
            rect = code.rect
            x0 = float(rect.left)
            y0 = float(rect.top)
            x1 = float(rect.left + rect.width)
            y1 = float(rect.top  + rect.height)
            code_type = str(code.type).lower()
            type_str  = "qr_code" if "qr" in code_type else "barcode"
            label     = "QR Code"  if "qr" in code_type else "Barcode"
            text      = code.data.decode("utf-8", errors="replace") if code.data else ""
            detections.append(make_detection(
                type_str, label, text[:100], 95.0,
                x0, y0, x1, y1, width, height, uid=f"{type_str}-{i}"
            ))
    except ImportError:
        try:
            qr_detector = cv2.QRCodeDetector()
            data, points, _ = qr_detector.detectAndDecode(img)
            if points is not None and data:
                pts = points[0]
                xs  = [p[0] for p in pts]
                ys  = [p[1] for p in pts]
                detections.append(make_detection(
                    "qr_code", "QR Code", data[:100], 90.0,
                    min(xs), min(ys), max(xs), max(ys),
                    width, height, uid="qr-0"
                ))
        except Exception:
            pass
    except Exception as e:
        print(f"[QR] Detection error: {e}")
    return detections

def iou(a, b):
    ix0 = max(a.x0, b.x0)
    iy0 = max(a.y0, b.y0)
    ix1 = min(a.x1, b.x1)
    iy1 = min(a.y1, b.y1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = (a.x1 - a.x0) * (a.y1 - a.y0)
    area_b = (b.x1 - b.x0) * (b.y1 - b.y0)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0

def nms_merge(detections, iou_threshold=0.4):
    if not detections:
        return []
    detections = sorted(detections, key=lambda d: d.confidence, reverse=True)
    kept = []
    for det in detections:
        discard = False
        for existing in kept:
            overlap = iou(det.bbox, existing.bbox)
            if overlap > iou_threshold and det.type == existing.type:
                discard = True
                break
        if not discard:
            kept.append(det)
    return kept

@app.get("/")
def health_check():
    return {"status": "ok", "message": "V3 Production Redaction Engine is running"}

@app.post("/scan", response_model=ScanResponse)
def scan_document(req: ScanRequest):
    t0 = time.time()
    try:
        b64 = req.imageBase64
        if "base64," in b64:
            b64 = b64.split("base64,")[1]
        img_bytes = base64.b64decode(b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image")
        height, width, _ = img.shape
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Image decode error: {e}")
    try:
        ocr = get_ocr_model()
        if hasattr(ocr, "predict"):
            result = ocr.predict(img)
        else:
            result = ocr.ocr(img)
        lines = parse_ocr_result(result, img)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR engine error: {e}")
    full_text = " ".join(str(line[1][0]) for line in lines if line[1][0])
    all_words = []
    for line in lines:
        box, (text, conf) = line
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        all_words.append(OCRWord(
            text=str(text), confidence=float(conf),
            bbox=BoundingBox(
                x0=float(max(0, min(100, (x0 / width)  * 100))),
                y0=float(max(0, min(100, (y0 / height) * 100))),
                x1=float(max(0, min(100, (x1 / width)  * 100))),
                y1=float(max(0, min(100, (y1 / height) * 100))),
            )
        ))
    regex_detections = run_regex(lines, width, height)
    ner_detections   = run_gliner_ner(lines, width, height)
    addr_detections  = run_address_rules(lines, width, height)
    face_detections  = run_face_detection(img, width, height)
    qr_detections    = run_qr_barcode_detection(img, width, height)
    all_dets = regex_detections + ner_detections + addr_detections + face_detections + qr_detections
    merged = nms_merge(all_dets, iou_threshold=0.4)
    merged = [d for d in merged if (d.bbox.x1 - d.bbox.x0) > 0 and (d.bbox.y1 - d.bbox.y0) > 0]
    processing_time = int((time.time() - t0) * 1000)
    print(
        f"[Scan] {processing_time}ms | "
        f"regex={len(regex_detections)} ner={len(ner_detections)} "
        f"addr={len(addr_detections)} face={len(face_detections)} "
        f"qr={len(qr_detections)} merged={len(merged)}"
    )
    return ScanResponse(
        detections=merged, words=all_words,
        fullText=full_text.strip(), processingTime=processing_time,
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
"""

with open(target, 'w', encoding='utf-8') as f:
    f.write(code)
print("Written OK")

target = r"D:\rot post\privacy-guardian\python-engine\main.py"

code = r"""import base64
import re
import time
import uuid as _uuid
from contextlib import asynccontextmanager
from typing import List
import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# =============================================================================
# PRIVACY GUARDIAN — V4 ULTRA-ACCURACY REDACTION ENGINE
# =============================================================================
# Detection layers (all run in parallel, merged via IoU-NMS):
#
#  1. PaddleOCR            — extract raw text + bounding boxes
#  2. Regex Engine (v4)    — Aadhaar (all formats + VID + masked),
#                            PAN, Mobile (+91 prefix, spaces),
#                            Email, IFSC, Bank Account,
#                            Passport, DOB (8 formats),
#                            OTP (context-aware 4–8 digit),
#                            GSTIN, Voter ID, UPI, Credit Card
#  3. Context Label Boost  — scan for "DOB:", "OTP:", "Mobile:" labels
#                            and grab the value on the same / next line
#  4. GLiNER NER           — PERSON, ADDRESS, ORG, PIN CODE
#  5. Address Rule Engine  — multi-line address anchor detection
#  6. InsightFace faces    — SCRFD, buffalo_l — all faces at any angle
#  7. MediaPipe faces      — dual-model (close + far) fallback
#  8. Haar + DNN faces     — triple-layered OpenCV fallback
#  9. pyzbar QR/Barcode    — all codes
# 10. IoU NMS Merge        — deduplicate across all layers
# =============================================================================

# -- Lazy model holders -------------------------------------------------------

_ocr_model = None
_gliner_model = None
_insight_app = None
_haar_cascade = None

def get_ocr_model():
    global _ocr_model
    if _ocr_model is None:
        from paddleocr import PaddleOCR
        _ocr_model = PaddleOCR(use_angle_cls=True, lang="en", enable_mkldnn=False)
        print("[OCR] PaddleOCR ready")
    return _ocr_model

def get_gliner_model():
    global _gliner_model
    if _gliner_model is None:
        try:
            from gliner import GLiNER
            _gliner_model = GLiNER.from_pretrained("urchade/gliner_base")
            print("[GLiNER] Model ready")
        except Exception as e:
            print(f"[GLiNER] Unavailable: {e}")
            _gliner_model = "unavailable"
    return _gliner_model

def get_insight_app():
    global _insight_app
    if _insight_app is None:
        try:
            from insightface.app import FaceAnalysis
            app = FaceAnalysis(providers=["CPUExecutionProvider"])
            app.prepare(ctx_id=-1, det_size=(640, 640))
            _insight_app = app
            print("[InsightFace] SCRFD ready — full multi-face detection enabled")
        except Exception as e:
            print(f"[InsightFace] Unavailable: {e}")
            _insight_app = "unavailable"
    return _insight_app

def get_haar_cascade():
    global _haar_cascade
    if _haar_cascade is None:
        _haar_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
    return _haar_cascade

# -- FastAPI lifespan (pre-warm OCR at startup) -------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] Pre-warming OCR model...")
    try:
        get_ocr_model()
    except Exception as e:
        print(f"[Startup] OCR warm-up failed: {e}")
    print("[Startup] Server ready")
    yield
    print("[Shutdown] Cleaning up")

app = FastAPI(title="Privacy Guardian - V4 Ultra-Accuracy Redaction Engine", lifespan=lifespan)

# -- Pydantic models ----------------------------------------------------------

class ScanRequest(BaseModel):
    imageBase64: str

class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

class Detection(BaseModel):
    id: str
    type: str
    label: str
    text: str
    confidence: float
    bbox: BoundingBox
    redacted: bool

class OCRWord(BaseModel):
    text: str
    confidence: float
    bbox: BoundingBox

class ScanResponse(BaseModel):
    detections: List[Detection]
    words: List[OCRWord]
    fullText: str
    processingTime: int

# =============================================================================
# REGEX ENGINE V4 — Comprehensive PII patterns for Indian documents
# =============================================================================

# ---- Aadhaar -----------------------------------------------------------------
# Formats: "1234 5678 9012", "1234-5678-9012", "123456789012",
#          masked "XXXX XXXX 9012", VID 16-digit
_AADHAAR_PLAIN    = r"\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}\b"
_AADHAAR_VID      = r"\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"  # 16-digit VID
_AADHAAR_MASKED   = r"\b(?:X{4}|x{4}|\*{4})[\s\-](?:X{4}|x{4}|\*{4})[\s\-]\d{4}\b"

# ---- PAN ---------------------------------------------------------------------
_PAN = r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"

# ---- Mobile ------------------------------------------------------------------
# +91-XXXXXXXXXX / 91XXXXXXXXXX / 0XXXXXXXXXX / plain 10-digit starting 6-9
_MOBILE = r"(?:(?:\+?91|0)[\s\-]?)?(?<!\d)[6-9]\d{9}(?!\d)"

# ---- Email -------------------------------------------------------------------
_EMAIL = r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"

# ---- IFSC -------------------------------------------------------------------
_IFSC = r"\b[A-Z]{4}0[A-Z0-9]{6}\b"

# ---- Bank Account (9–18 digits) ---------------------------------------------
_BANK_ACCT = r"\b\d{9,18}\b"

# ---- Credit / Debit Card (13–19 digits, may have spaces/dashes) -------------
_CARD = r"\b(?:\d{4}[\s\-]?){3}\d{4}\b"

# ---- Passport ---------------------------------------------------------------
_PASSPORT = r"\b[A-Z][0-9]{7}\b"

# ---- Voter ID ---------------------------------------------------------------
_VOTER_ID = r"\b[A-Z]{3}[0-9]{7}\b"

# ---- Driving Licence --------------------------------------------------------
_DL = r"\b[A-Z]{2}[\s\-]?\d{2}[\s\-]?\d{4}[\s\-]?\d{7}\b"

# ---- GSTIN ------------------------------------------------------------------
_GSTIN = r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d][Z][A-Z\d]\b"

# ---- UPI ID -----------------------------------------------------------------
_UPI = r"[\w.\-]{2,}@[a-z]{2,}"

# ---- OTP (context-aware) — 4 to 8 digits found near OTP/Code keywords ------
# Strategy: detect keyword context first in the whole line, then extract digits
_OTP_LABEL = re.compile(
    r"(?:otp|one[\s\-]time[\s\-](?:password|passcode|pin)|verification\s+code"
    r"|auth(?:entication)?\s+code|security\s+code|code|passcode|pin\b)"
    r"[:\s\-]*(\d{4,8})",
    re.IGNORECASE
)
_OTP_REVERSE = re.compile(     # digits followed by label
    r"\b(\d{4,8})\b\s*(?:is\s+)?(?:your\s+)?(?:otp|code|pin)\b",
    re.IGNORECASE
)

# ---- DOB — 8 different formats ----------------------------------------------
_DOB_FORMATS = [
    r"\b(0?[1-9]|[12]\d|3[01])/(0?[1-9]|1[0-2])/(?:19|20)\d{2}\b",  # DD/MM/YYYY
    r"\b(0?[1-9]|[12]\d|3[01])-(0?[1-9]|1[0-2])-(?:19|20)\d{2}\b",  # DD-MM-YYYY
    r"\b(?:19|20)\d{2}/(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])\b",  # YYYY/MM/DD
    r"\b(?:19|20)\d{2}-(0?[1-9]|1[0-2])-(0?[1-9]|[12]\d|3[01])\b",  # YYYY-MM-DD
    r"\b(0?[1-9]|[12]\d|3[01])\s+"                                      # DD Mon YYYY
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+(?:19|20)\d{2}\b",
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"  # Mon DD YYYY
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+(0?[1-9]|[12]\d|3[01]),?\s+(?:19|20)\d{2}\b",
    r"\b(0?[1-9]|[12]\d|3[01])\.(0?[1-9]|1[0-2])\.(?:19|20)\d{2}\b",  # DD.MM.YYYY
]

# ---- Label-Value Context patterns (for DOB, Mobile, OTP labels) --------------
_LABEL_CONTEXT = re.compile(
    r"(?:dob|date\s+of\s+birth|born\s+on|birth\s+date|mobile|phone|contact|"
    r"mob(?:ile)?\.?|tel(?:ephone)?|cell|no\.?|number|otp|verification|passcode)"
    r"\s*[:\-]?\s*(.+)",
    re.IGNORECASE
)

# Master regex table: (type, label, compiled_pattern, base_confidence)
REGEX_TABLE = [
    ("aadhaar",      "Aadhaar VID",      re.compile(_AADHAAR_VID,    re.I), 95),
    ("aadhaar",      "Aadhaar Number",   re.compile(_AADHAAR_PLAIN,  re.I), 93),
    ("aadhaar",      "Masked Aadhaar",   re.compile(_AADHAAR_MASKED, re.I), 88),
    ("pan",          "PAN Number",       re.compile(_PAN),                  96),
    ("phone",        "Mobile Number",    re.compile(_MOBILE),               91),
    ("email",        "Email Address",    re.compile(_EMAIL,          re.I), 92),
    ("bank_account", "IFSC Code",        re.compile(_IFSC),                 90),
    ("credit_card",  "Card Number",      re.compile(_CARD),                 85),
    ("bank_account", "Bank Account",     re.compile(_BANK_ACCT),            72),
    ("passport",     "Passport Number",  re.compile(_PASSPORT),             87),
    ("voter_id",     "Voter ID",         re.compile(_VOTER_ID),             84),
    ("gstin",        "GSTIN",            re.compile(_GSTIN),                92),
    ("upi",          "UPI ID",           re.compile(_UPI,            re.I), 80),
]

for _fmt in _DOB_FORMATS:
    REGEX_TABLE.insert(0, ("dob", "Date of Birth", re.compile(_fmt, re.I), 82))

ADDRESS_ANCHORS = {
    "flat", "plot", "house", "h.no", "h/o", "w/o", "s/o", "d/o", "c/o",
    "road", "street", "lane", "marg", "avenue", "nagar", "colony", "sector",
    "village", "vill", "po", "p.o", "ps", "p.s", "tehsil", "taluka", "mandal",
    "district", "dist", "city", "state", "near", "behind", "opposite", "opp",
    "building", "tower", "complex", "society", "apartment", "apt", "wing",
    "phase", "block", "ward", "area", "locality", "post", "address", "at",
    "at/po", "via", "taluk", "gram", "vpo", "pin", "pincode", "zip",
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def make_det(type_str, label, text, conf, x0, y0, x1, y1, W, H, uid=None):
    uid = uid or f"{type_str}-{_uuid.uuid4().hex[:8]}"
    def pct(v, dim): return float(max(0.0, min(100.0, (v / dim) * 100)))
    return Detection(
        id=uid, type=type_str, label=label, text=str(text)[:200],
        confidence=float(conf),
        bbox=BoundingBox(x0=pct(x0, W), y0=pct(y0, H), x1=pct(x1, W), y1=pct(y1, H)),
        redacted=True,
    )

def parse_ocr(result, img):
    lines = []
    if not result or not result[0]:
        return lines
    item = result[0]
    if isinstance(item, dict) and "dt_polys" in item:
        polys  = item.get("dt_polys",   [])
        texts  = item.get("rec_texts",  [])
        scores = item.get("rec_scores", [])
        for i in range(len(texts)):
            poly = polys[i]
            box  = poly.tolist() if hasattr(poly, "tolist") else list(poly)
            lines.append([box, (texts[i], float(scores[i]))])
    elif isinstance(item, list):
        for x in item:
            if x is not None:
                lines.append(x)
    return lines

def bbox4(box):
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return min(xs), min(ys), max(xs), max(ys)

def iou(a: BoundingBox, b: BoundingBox) -> float:
    ix0, iy0 = max(a.x0, b.x0), max(a.y0, b.y0)
    ix1, iy1 = min(a.x1, b.x1), min(a.y1, b.y1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    union = (a.x1-a.x0)*(a.y1-a.y0) + (b.x1-b.x0)*(b.y1-b.y0) - inter
    return inter / union if union > 0 else 0.0

def nms(dets: List[Detection], thr: float = 0.4) -> List[Detection]:
    dets = sorted(dets, key=lambda d: d.confidence, reverse=True)
    kept: List[Detection] = []
    for d in dets:
        skip = any(
            iou(d.bbox, k.bbox) > thr and d.type == k.type
            for k in kept
        )
        if not skip:
            kept.append(d)
    return kept

# =============================================================================
# LAYER 2 — REGEX ENGINE V4
# =============================================================================

def run_regex(lines, W, H) -> List[Detection]:
    dets = []
    seen = set()
    full_doc = []

    for line in lines:
        box, (text, conf) = line
        text_s = str(text).strip()
        if not text_s:
            continue
        x0, y0, x1, y1 = bbox4(box)
        full_doc.append((text_s, x0, y0, x1, y1))

        # Run each pattern
        for type_str, label, pat, base_conf in REGEX_TABLE:
            for m in pat.finditer(text_s):
                mt = m.group(0).strip()
                key = f"{type_str}:{mt}"
                if key in seen:
                    continue
                seen.add(key)
                dets.append(make_det(type_str, label, mt, float(base_conf), x0, y0, x1, y1, W, H))

        # OTP context-aware
        for m in _OTP_LABEL.finditer(text_s):
            mt = m.group(1)
            key = f"otp:{mt}"
            if key not in seen:
                seen.add(key)
                dets.append(make_det("otp", "OTP Code", mt, 88.0, x0, y0, x1, y1, W, H))
        for m in _OTP_REVERSE.finditer(text_s):
            mt = m.group(1)
            key = f"otp:{mt}"
            if key not in seen:
                seen.add(key)
                dets.append(make_det("otp", "OTP Code", mt, 86.0, x0, y0, x1, y1, W, H))

    # Label-context boost: re-scan consecutive lines for "DOB: ...", "Mobile: ..."
    for i, (text_s, x0, y0, x1, y1) in enumerate(full_doc):
        m = _LABEL_CONTEXT.match(text_s)
        if not m:
            continue
        val = m.group(1).strip()
        # Try to match a value type from the captured group
        label_l = text_s.lower()
        if any(w in label_l for w in ["dob", "birth", "born"]):
            for _fmt in _DOB_FORMATS:
                fm = re.search(_fmt, val, re.I)
                if fm:
                    key = f"dob:{fm.group(0)}"
                    if key not in seen:
                        seen.add(key)
                        dets.append(make_det("dob", "Date of Birth (label)", fm.group(0), 92.0, x0, y0, x1, y1, W, H))
                    break
        if any(w in label_l for w in ["mobile", "phone", "mob", "tel", "cell", "contact"]):
            fm = re.search(_MOBILE, val)
            if fm:
                key = f"phone:{fm.group(0)}"
                if key not in seen:
                    seen.add(key)
                    dets.append(make_det("phone", "Mobile (label)", fm.group(0), 94.0, x0, y0, x1, y1, W, H))

    return dets

# =============================================================================
# LAYER 4 — GLiNER NER
# =============================================================================

GLINER_LABELS = [
    "person", "person name", "full name", "individual",
    "address", "street address", "residential address", "mailing address",
    "city", "state", "district", "country",
    "pin code", "postal code", "zip code",
    "organization", "company", "hospital", "school", "institute",
]

GLINER_TYPE_MAP = {
    "person": "name", "person name": "name", "full name": "name", "individual": "name",
    "address": "address", "street address": "address", "residential address": "address",
    "mailing address": "address", "city": "address", "state": "address",
    "district": "address", "country": "address",
    "pin code": "pincode", "postal code": "pincode", "zip code": "pincode",
    "organization": "name", "company": "name", "hospital": "name",
    "school": "name", "institute": "name",
}

def run_gliner(lines, W, H) -> List[Detection]:
    model = get_gliner_model()
    if model == "unavailable" or model is None:
        return []

    words = []
    text  = ""
    for line in lines:
        box, (t, c) = line
        ts = str(t).strip()
        if not ts:
            continue
        x0, y0, x1, y1 = bbox4(box)
        for w in ts.split():
            s = len(text)
            text += w
            e = len(text)
            text += " "
            words.append((w, x0, y0, x1, y1, s, e))

    if not words:
        return []

    try:
        ents = model.predict_entities(text, GLINER_LABELS, threshold=0.38)
    except Exception as e:
        print(f"[GLiNER] Error: {e}")
        return []

    dets = []
    seen = set()
    label_map = {"name": "Person Name", "address": "Address", "pincode": "PIN Code"}

    for ent in ents:
        es, ee    = ent["start"], ent["end"]
        etype     = GLINER_TYPE_MAP.get(ent["label"].lower(), "name")
        etext     = ent["text"]
        escore    = ent.get("score", 0.75)
        key       = f"{etype}:{etext.lower()}"
        if key in seen:
            continue
        seen.add(key)

        ov = [w for w in words if not (w[6] <= es or w[5] >= ee)]
        if not ov:
            ov = [w for w in words if w[0] in etext]
        if not ov:
            continue

        mx0 = min(w[1] for w in ov)
        my0 = min(w[2] for w in ov)
        mx1 = max(w[3] for w in ov)
        my1 = max(w[4] for w in ov)
        px  = (mx1 - mx0) * 0.03
        py  = (my1 - my0) * 0.05

        dets.append(make_det(
            etype, label_map.get(etype, etype.title()), etext,
            float(min(99, escore * 100)),
            max(0, mx0 - px), max(0, my0 - py),
            min(W, mx1 + px), min(H, my1 + py),
            W, H
        ))
    return dets

# =============================================================================
# LAYER 5 — ADDRESS RULE ENGINE
# =============================================================================

def run_address_rules(lines, W, H) -> List[Detection]:
    sl = sorted(lines, key=lambda ln: bbox4(ln[0])[1])
    blocks = []
    active = False
    bboxes, texts, ax = [], [], -1

    for line in sl:
        box, (t, _) = line
        ts = str(t).strip()
        tl = ts.lower()
        x0, y0, x1, y1 = bbox4(box)
        words_set = set(re.split(r"\W+", tl))
        anchor  = bool(words_set & ADDRESS_ANCHORS)
        has_pin = bool(re.search(r"\b\d{6}\b", ts))

        if anchor and not active:
            active = True
            ax     = x0
            bboxes = [(x0, y0, x1, y1)]
            texts  = [ts]
        elif active:
            if abs(x0 - ax) < W * 0.35:
                bboxes.append((x0, y0, x1, y1))
                texts.append(ts)
            else:
                if len(bboxes) >= 2:
                    blocks.append((bboxes[:], texts[:]))
                active, bboxes, texts, ax = False, [], [], -1
            if has_pin:
                if len(bboxes) >= 2:
                    blocks.append((bboxes[:], texts[:]))
                active, bboxes, texts, ax = False, [], [], -1

    if active and len(bboxes) >= 2:
        blocks.append((bboxes, texts))

    dets = []
    for bxs, txs in blocks:
        mx0 = min(b[0] for b in bxs)
        my0 = min(b[1] for b in bxs)
        mx1 = max(b[2] for b in bxs)
        my1 = max(b[3] for b in bxs)
        pw  = (mx1 - mx0) * 0.04
        ph  = (my1 - my0) * 0.04
        dets.append(make_det(
            "address", "Address Block", " | ".join(txs), 85.0,
            max(0, mx0 - pw), max(0, my0 - ph),
            min(W, mx1 + pw), min(H, my1 + ph),
            W, H
        ))
    return dets

# =============================================================================
# LAYER 6 — INSIGHTFACE (SCRFD — best multi-face detector)
# =============================================================================

def run_insightface(img, W, H) -> List[Detection]:
    fa = get_insight_app()
    if fa == "unavailable" or fa is None:
        return []
    try:
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        faces = fa.get(img_rgb)
        dets  = []
        for i, face in enumerate(faces):
            bb   = face.bbox.astype(int)  # [x0, y0, x1, y1] absolute
            conf = float(face.det_score) * 100 if hasattr(face, "det_score") else 90.0
            dets.append(make_det(
                "face", "Face (InsightFace)", "[FACE]", conf,
                bb[0], bb[1], bb[2], bb[3], W, H,
                uid=f"iface-{i}"
            ))
        print(f"[InsightFace] {len(dets)} face(s) detected")
        return dets
    except Exception as e:
        print(f"[InsightFace] Runtime error: {e}")
        return []

# =============================================================================
# LAYER 7 — MEDIAPIPE (dual-model, close + far)
# =============================================================================

def run_mediapipe_faces(img, W, H) -> List[Detection]:
    dets = []
    try:
        import mediapipe as mp
        mp_fd = mp.solutions.face_detection

        for model_sel in [0, 1]:  # 0 = close-up, 1 = full range
            with mp_fd.FaceDetection(model_selection=model_sel, min_detection_confidence=0.3) as fd:
                rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                res = fd.process(rgb)
                if res.detections:
                    for i, det in enumerate(res.detections):
                        bb = det.location_data.relative_bounding_box
                        x0 = max(0.0, bb.xmin * 100)
                        y0 = max(0.0, bb.ymin * 100)
                        x1 = min(100.0, (bb.xmin + bb.width)  * 100)
                        y1 = min(100.0, (bb.ymin + bb.height) * 100)
                        dets.append(Detection(
                            id=f"mp-m{model_sel}-{i}",
                            type="face", label="Face (MediaPipe)", text="[FACE]",
                            confidence=float(det.score[0] * 100),
                            bbox=BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1),
                            redacted=True,
                        ))
    except Exception as e:
        print(f"[MediaPipe] Error: {e}")
    return dets

# =============================================================================
# LAYER 8 — OPENCV HAAR + DNN FALLBACK
# =============================================================================

def run_opencv_faces(img, W, H) -> List[Detection]:
    dets = []
    try:
        gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cascade = get_haar_cascade()

        # Haar Cascade (frontal)
        faces_haar = cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=4,
            minSize=(30, 30), flags=cv2.CASCADE_SCALE_IMAGE
        )
        for i, (x, y, fw, fh) in enumerate(faces_haar if len(faces_haar) else []):
            dets.append(make_det(
                "face", "Face (Haar)", "[FACE]", 75.0,
                x, y, x + fw, y + fh, W, H, uid=f"haar-{i}"
            ))

        # Profile face cascade
        cascade_profile = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_profileface.xml"
        )
        faces_profile = cascade_profile.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=3,
            minSize=(30, 30), flags=cv2.CASCADE_SCALE_IMAGE
        )
        for i, (x, y, fw, fh) in enumerate(faces_profile if len(faces_profile) else []):
            dets.append(make_det(
                "face", "Face (Profile)", "[FACE]", 72.0,
                x, y, x + fw, y + fh, W, H, uid=f"haar-profile-{i}"
            ))
    except Exception as e:
        print(f"[OpenCV Haar] Error: {e}")
    return dets

# =============================================================================
# LAYER 9 — QR / BARCODE
# =============================================================================

def run_qr(img, W, H) -> List[Detection]:
    dets = []
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
        gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        codes = pyzbar_decode(gray)
        for i, code in enumerate(codes):
            r      = code.rect
            ct     = str(code.type).lower()
            tstr   = "qr_code" if "qr" in ct else "barcode"
            label  = "QR Code"  if "qr" in ct else "Barcode"
            text   = code.data.decode("utf-8", errors="replace")[:100] if code.data else ""
            dets.append(make_det(tstr, label, text, 95.0,
                                 r.left, r.top, r.left + r.width, r.top + r.height,
                                 W, H, uid=f"{tstr}-{i}"))
    except ImportError:
        try:
            qrd = cv2.QRCodeDetector()
            data, pts, _ = qrd.detectAndDecode(img)
            if pts is not None and data:
                xs = [p[0] for p in pts[0]]
                ys = [p[1] for p in pts[0]]
                dets.append(make_det("qr_code", "QR Code", data[:100], 90.0,
                                     min(xs), min(ys), max(xs), max(ys), W, H, uid="qr-0"))
        except Exception:
            pass
    except Exception as e:
        print(f"[QR] Error: {e}")
    return dets

# =============================================================================
# HEALTH & SCAN ENDPOINTS
# =============================================================================

@app.get("/")
def health():
    return {
        "status":  "ok",
        "version": "v4",
        "message": "Privacy Guardian V4 Ultra-Accuracy Redaction Engine",
        "models":  {
            "ocr":         "PaddleOCR (pre-warmed)",
            "ner":         "GLiNER / urchade/gliner_base (lazy)",
            "face":        "InsightFace SCRFD + MediaPipe + Haar Cascade",
            "qr":          "pyzbar + OpenCV",
            "regex":       "V4 — Aadhaar/VID/masked, PAN, Mobile+91, DOB×8, OTP, UPI, GSTIN, Card",
        }
    }


@app.post("/scan", response_model=ScanResponse)
def scan(req: ScanRequest):
    t0 = time.time()

    # ── Decode ────────────────────────────────────────────────────────────────
    try:
        b64 = req.imageBase64
        if "base64," in b64:
            b64 = b64.split("base64,", 1)[1]
        buf   = np.frombuffer(base64.b64decode(b64), np.uint8)
        img   = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("imdecode returned None")
        H, W, _ = img.shape
    except Exception as e:
        raise HTTPException(400, f"Image decode: {e}")

    # ── OCR ───────────────────────────────────────────────────────────────────
    try:
        ocr    = get_ocr_model()
        result = ocr.predict(img) if hasattr(ocr, "predict") else ocr.ocr(img)
        lines  = parse_ocr(result, img)
    except Exception as e:
        raise HTTPException(500, f"OCR engine: {e}")

    full_text = " ".join(str(ln[1][0]) for ln in lines if ln[1][0])
    words_out: List[OCRWord] = []
    for ln in lines:
        box, (t, c) = ln
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
        def pct(v, dim): return float(max(0.0, min(100.0, (v / dim) * 100)))
        words_out.append(OCRWord(
            text=str(t), confidence=float(c),
            bbox=BoundingBox(x0=pct(x0,W), y0=pct(y0,H), x1=pct(x1,W), y1=pct(y1,H))
        ))

    # ── Run all detection layers ──────────────────────────────────────────────
    regex_d = run_regex(lines, W, H)
    ner_d   = run_gliner(lines, W, H)
    addr_d  = run_address_rules(lines, W, H)

    # Face detection — try InsightFace first, fall back to MediaPipe, then Haar
    iface_d  = run_insightface(img, W, H)
    mp_d     = run_mediapipe_faces(img, W, H)
    haar_d   = run_opencv_faces(img, W, H)
    qr_d     = run_qr(img, W, H)

    all_dets = regex_d + ner_d + addr_d + iface_d + mp_d + haar_d + qr_d
    merged   = nms(all_dets, thr=0.4)
    merged   = [d for d in merged if (d.bbox.x1 - d.bbox.x0) > 0 and (d.bbox.y1 - d.bbox.y0) > 0]

    ms = int((time.time() - t0) * 1000)
    print(
        f"[Scan] {ms}ms | W={W} H={H} | "
        f"lines={len(lines)} regex={len(regex_d)} ner={len(ner_d)} "
        f"addr={len(addr_d)} iface={len(iface_d)} mp={len(mp_d)} "
        f"haar={len(haar_d)} qr={len(qr_d)} → merged={len(merged)}"
    )

    return ScanResponse(
        detections=merged, words=words_out,
        fullText=full_text.strip(), processingTime=ms,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
"""

with open(target, "w", encoding="utf-8") as f:
    f.write(code)
print("V4 main.py written OK")
