import base64
import re
import time
import uuid as _uuid
import sys
from contextlib import asynccontextmanager
from typing import List, Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

import cv2
import numpy as np
import psutil
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# =============================================================================
# PRIVACY GUARDIAN -- V6 MULTI-MODEL 11-LAYER PIPELINE
# =============================================================================
# Ordered linear pipeline (no DAG, no silent failures):
#   L1.  Image decode + CLAHE preprocessing
#   L2.  PaddleOCR (primary) + EasyOCR (fallback/supplement)
#   L3.  Regex Engine  -- Indian PII (Aadhaar, PAN, mobile, plate...)
#   L4.  Address Rule Engine -- shipping label blocks
#   L5.  Full-Text Scan -- joins OCR boxes for split tokens
#   L6.  InsightFace / MediaPipe / Haar -- face detection
#   L7.  QR/Barcode    -- pyzbar
#   L8.  YOLOv8n       -- persons, weapons, vehicles
#   L9.  NudeNet       -- NSFW body-part detection (auto-blur)
#  L10.  fast-alpr     -- License plate detector + OCR (global)
#  L11.  Signature     -- heuristic connected-component detector
#  L12.  Doc Classifier-- medical / legal / financial keyword flagging
# =============================================================================


_ocr_paddle = None
_ocr_easy = None
_insight_app = None
_yolo_model = None
_nudenet_classifier = None
_alpr_detector = None

def get_paddle_ocr():
    global _ocr_paddle
    if _ocr_paddle is None:
        try:
            from paddleocr import PaddleOCR
            _ocr_paddle = PaddleOCR(use_angle_cls=True, lang="en", enable_mkldnn=False, cpu_threads=4)
            print("[OCR] PaddleOCR ready")
        except Exception as e:
            print(f"[OCR] PaddleOCR unavailable: {e}")
            _ocr_paddle = "unavailable"
    return _ocr_paddle

def get_easyocr():
    global _ocr_easy
    if _ocr_easy is None:
        try:
            import easyocr
            _ocr_easy = easyocr.Reader(['en', 'hi'], gpu=False)
            print("[OCR] EasyOCR ready")
        except Exception as e:
            print(f"[OCR] EasyOCR unavailable: {e}")
            _ocr_easy = "unavailable"
    return _ocr_easy

def get_insight_app():
    global _insight_app
    if _insight_app is None:
        try:
            from insightface.app import FaceAnalysis
            _insight_app = FaceAnalysis(name="buffalo_sc", providers=["CPUExecutionProvider"])
            _insight_app.prepare(ctx_id=-1, det_size=(640, 640))
            print("[InsightFace] Ready")
        except Exception as e:
            print(f"[InsightFace] Unavailable: {e}")
            _insight_app = "unavailable"
    return _insight_app

def get_yolo():
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            _yolo_model = YOLO("yolov8n.pt")
            print("[YOLO] YOLOv8n ready")
        except Exception as e:
            print(f"[YOLO] Unavailable: {e}")
            _yolo_model = "unavailable"
    return _yolo_model

def get_nudenet():
    global _nudenet_classifier
    if _nudenet_classifier is None:
        try:
            from nudenet import NudeDetector
            _nudenet_classifier = NudeDetector()
            print("[NudeNet] Ready")
        except Exception as e:
            print(f"[NudeNet] Unavailable: {e}")
            _nudenet_classifier = "unavailable"
    return _nudenet_classifier

def get_alpr():
    global _alpr_detector
    if _alpr_detector is None:
        try:
            from fast_alpr import ALPR
            _alpr_detector = ALPR(
                detector_model="yolo-v9-t-640-license-plate-end2end",
                ocr_model="global-plates-mobile-vit-v2-model",
            )
            print("[ALPR] fast-alpr ready")
        except Exception as e:
            print(f"[ALPR] Unavailable: {e}")
            _alpr_detector = "unavailable"
    return _alpr_detector

# FastAPI lifespan -- pre-warm OCR at startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] Pre-warming OCR models...")
    get_paddle_ocr()
    get_easyocr()
    # Pre-warm NudeNet in background (first load downloads model ~93MB)
    import threading
    threading.Thread(target=get_nudenet, daemon=True).start()
    threading.Thread(target=get_alpr,    daemon=True).start()
    print("[Startup] Server ready (NudeNet + ALPR loading in background)")
    yield
    print("[Shutdown] Done")

app = FastAPI(title="Privacy Guardian V5 - Reliable Linear Pipeline", lifespan=lifespan)

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ScanRequest(BaseModel):
    imageBase64: str
    trusted_faces_base64: Optional[List[str]] = None

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
    source: str = "unknown"
    polygon: Optional[List[float]] = None

class OCRWord(BaseModel):
    text: str
    confidence: float
    bbox: BoundingBox

class FeedbackCorrection(BaseModel):
    type: str
    bbox: BoundingBox
    polygon: Optional[List[float]] = None

class FeedbackRequest(BaseModel):
    image: str
    corrections: List[FeedbackCorrection]

class SystemMetrics(BaseModel):
    ocr_latency_ms: int = 0
    total_latency_ms: int = 0
    redaction_coverage_pct: float = 0.0
    memory_usage_mb: float = 0.0

class ScanResponse(BaseModel):
    detections: List[Detection]
    words: List[OCRWord]
    fullText: str
    processingTime: int
    aiDescription: str = ""
    privacyScore: int = 55
    metrics: Optional[SystemMetrics] = None
    diagnostics: Optional[dict[str, str]] = None

# =============================================================================
# REGEX PATTERNS -- Indian PII + Shipping Labels
# =============================================================================

# Aadhaar: 12 digits in groups of 4
_RE_AADHAAR = re.compile(r"\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}\b")
# PAN: ABCDE1234F
_RE_PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
# Indian mobile: 10 digits starting 6-9, optional +91/0 prefix, allows spaces/dashes between digits
_RE_MOBILE = re.compile(r"(?:(?:\+?91|0)[\s\-]?)?(?<!\d)[6-9](?:[\s\-]*\d){9}(?!\d)")
# Email
_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", re.I)
# IFSC
_RE_IFSC = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b")
# Credit/Debit card -- 16 digits
_RE_CARD = re.compile(r"\b(?:\d{4}[\s\-]?){3}\d{4}\b")
# Passport
_RE_PASSPORT = re.compile(r"\b[A-Z][0-9]{7}\b")
# Voter ID
_RE_VOTER = re.compile(r"\b[A-Z]{3}[0-9]{7}\b")
# GSTIN
_RE_GSTIN = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d][Z][A-Z\d]\b")
# Tracking numbers (alphanumeric, 10-20 chars like DTDC, Delhivery, Blue Dart)
_RE_TRACKING = re.compile(r"\b[A-Z0-9]{10,20}\b")
# EMS / Speed Post tracking (e.g. EM 123456789 IN)
_RE_EMS_TRACKING = re.compile(r"\b[A-Z]{2}[\s\-]*\d{9}[\s\-]*[A-Z]{2}\b", re.I)
# PIN code (Indian 6-digit)
_RE_PINCODE = re.compile(r"\b[1-9](?:[\s\-]*\d){5}\b")
# DOB formats
_RE_DOB = re.compile(
    r"\b(?:"
    r"\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}"  # DD/MM/YYYY or DD-MM-YY
    r"|(?:0?[1-9]|[12]\d|3[01])\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(?:19|20)\d{2}"
    r")\b",
    re.I
)
# Indian vehicle license plate: MH12AB1234 or BH6517A format
# Also handles OCR artifacts like "22BH6517A IND" (IND watermark reads as extra chars)
_RE_PLATE = re.compile(
    r"\b(?:"
    r"[A-Z]{2}\s*\d{2}\s*[A-Z]{1,3}\s*\d{1,4}"  # standard: MH12AB1234
    r"|(?:\d{1,2}\s*)?BH\s*\d{2,4}\s*[A-Z]{1,2}" # BH series with optional leading digit
    r")\b",
    re.ASCII
)

# Master regex table: (type, label, pattern, confidence)
REGEX_TABLE = [
    ("aadhaar",       "Aadhaar Number",    _RE_AADHAAR,    95.0),
    ("pan",           "PAN Number",        _RE_PAN,        96.0),
    ("phone",         "Mobile Number",     _RE_MOBILE,     91.0),
    ("email",         "Email Address",     _RE_EMAIL,      92.0),
    ("bank_account",  "IFSC Code",         _RE_IFSC,       90.0),
    ("credit_card",   "Card Number",       _RE_CARD,       85.0),
    ("passport",      "Passport Number",   _RE_PASSPORT,   87.0),
    ("voter_id",      "Voter ID",          _RE_VOTER,      84.0),
    ("gstin",         "GSTIN",             _RE_GSTIN,      92.0),
    ("dob",           "Date of Birth",     _RE_DOB,        85.0),
    ("pincode",       "PIN Code",          _RE_PINCODE,    80.0),
    ("tracking",      "Speed Post / EMS",  _RE_EMS_TRACKING, 90.0),
    ("license_plate", "Vehicle Number",    _RE_PLATE,      88.0),
]

# Address anchor keywords -- shipping labels always have these
ADDRESS_ANCHORS = {
    "flat", "plot", "house", "h.no", "h/o", "w/o", "s/o", "d/o", "c/o",
    "road", "street", "lane", "marg", "avenue", "nagar", "colony", "sector",
    "village", "vill", "po", "p.o", "ps", "p.s", "tehsil", "taluka", "mandal",
    "district", "dist", "city", "state", "pin", "pincode", "zip",
    "to", "from", "at/po", "at", "phone", "mob", "mobile", "ph", "contact",
    "near", "behind", "opposite", "opp",
    "building", "tower", "complex", "society", "apartment", "apt", "wing",
    "phase", "block", "ward", "area", "locality", "post", "address",
    "via", "taluk", "gram", "vpo",
    "receiver", "sender", "deliver", "delivery", "ship",
    "berhampur", "odisha", "dtdc", "express", "india", "courier",
    # Generic shipping label triggers
    "berhampur", "bhubaneswar", "berhampur", "ho",
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def make_det(type_str, label, text, conf, x0, y0, x1, y1, W, H,
             uid=None, force_redact=False, source="unknown", polygon=None):
    uid = uid or f"{type_str}-{_uuid.uuid4().hex[:8]}"
    def pct(v, dim): return float(max(0.0, min(100.0, (v / dim) * 100.0)))
    auto = force_redact or (conf >= 70.0)
    
    # Append the source engine to the label so the user knows what detected it
    if source != "unknown":
        # Format it nicely: source='insightface' -> 'Insightface'
        clean_source = source.replace("_", " ").title()
        label = f"{label} ({clean_source})"

    return Detection(
        id=uid, type=type_str, label=label, text=str(text)[:300],
        confidence=float(conf),
        bbox=BoundingBox(x0=pct(x0, W), y0=pct(y0, H), x1=pct(x1, W), y1=pct(y1, H)),
        redacted=auto,
        source=source,
        polygon=polygon
    )

def bbox4(box):
    """Get min bounding rect from polygon points [[x,y], ...]"""
    xs = [float(p[0]) for p in box]
    ys = [float(p[1]) for p in box]
    return min(xs), min(ys), max(xs), max(ys)

def iou(a: BoundingBox, b: BoundingBox) -> float:
    ix0, iy0 = max(a.x0, b.x0), max(a.y0, b.y0)
    ix1, iy1 = min(a.x1, b.x1), min(a.y1, b.y1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    union = (a.x1 - a.x0) * (a.y1 - a.y0) + (b.x1 - b.x0) * (b.y1 - b.y0) - inter
    return inter / union if union > 0 else 0.0

def nms(dets: List[Detection], thr: float = 0.5) -> List[Detection]:
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
# LAYER 1 -- OCR (PaddleOCR primary, EasyOCR fallback)
# =============================================================================

def run_ocr(img) -> list:
    """
    Returns lines in format: [ [[x0,y0],[x1,y0],[x1,y1],[x0,y1]], (text, conf) ]
    """
    lines = []

    # --- PaddleOCR ---
    paddle = get_paddle_ocr()
    if paddle != "unavailable" and paddle is not None:
        try:
            # Try new API first (predict), fall back to ocr()
            if hasattr(paddle, 'predict'):
                result = paddle.predict(img)
            else:
                result = paddle.ocr(img, cls=True)

            if result and result[0]:
                r0 = result[0]
                # New PaddleOCR API returns dict with dt_polys
                if isinstance(r0, dict) and "dt_polys" in r0:
                    polys  = r0.get("dt_polys", [])
                    texts  = r0.get("rec_texts", [])
                    scores = r0.get("rec_scores", [])
                    for i in range(len(texts)):
                        poly = polys[i]
                        box = poly.tolist() if hasattr(poly, "tolist") else list(poly)
                        t, c = texts[i], float(scores[i])
                        if str(t).strip() and c > 0.2:
                            lines.append([box, (str(t), c)])
                elif isinstance(r0, list):
                    for item in r0:
                        if item is None:
                            continue
                        # item = [box, (text, conf)]
                        if isinstance(item, (list, tuple)) and len(item) == 2:
                            box, tc = item
                            if isinstance(tc, (list, tuple)) and len(tc) == 2:
                                t, c = str(tc[0]), float(tc[1])
                                if t.strip() and c > 0.2:
                                    lines.append([box, (t, c)])
            print(f"[OCR] PaddleOCR found {len(lines)} lines")
        except Exception as e:
            print(f"[OCR] PaddleOCR error: {e}")

    # --- EasyOCR (fallback only to improve speed) ---
    if len(lines) < 2:
        easy = get_easyocr()
        if easy != "unavailable" and easy is not None:
            try:
                easy_results = easy.readtext(img)
                easy_count = 0
                for detection in easy_results:
                    box, text, conf = detection
                    if str(text).strip() and float(conf) > 0.2:
                        clean_box = [[float(pt[0]), float(pt[1])] for pt in box]
                        lines.append([clean_box, (str(text), float(conf))])
                        easy_count += 1
                print(f"[OCR] EasyOCR added {easy_count} lines (Fallback)")
            except Exception as e:
                print(f"[OCR] EasyOCR error: {e}")

    if not lines:
        print("[OCR] WARNING: No text detected by any OCR engine!")
    else:
        full_text = " ".join(str(ln[1][0]) for ln in lines)
        safe_sample = full_text[:200].encode('ascii', errors='ignore').decode('ascii')
        print(f"[OCR] Total {len(lines)} lines | Sample: {safe_sample}")

    return lines

# =============================================================================
# LAYER 2 -- REGEX ENGINE
# =============================================================================

def run_regex(lines, W, H) -> List[Detection]:
    dets = []
    seen = set()

    for line in lines:
        box, (text, conf) = line
        text_s = str(text).strip()
        if not text_s:
            continue
        x0, y0, x1, y1 = bbox4(box)

        for type_str, label, pat, base_conf in REGEX_TABLE:
            for m in pat.finditer(text_s):
                mt = m.group(0).strip()
                key = f"{type_str}:{mt}"
                if key in seen:
                    continue
                seen.add(key)
                dets.append(make_det(type_str, label, mt, base_conf, x0, y0, x1, y1, W, H, source="regex"))
                print(f"  [Regex] Found {label}: '{mt}' conf={base_conf}")

    print(f"[Regex] Total: {len(dets)} PII matches")
    return dets

# =============================================================================
# LAYER 3 -- ADDRESS / NAME BLOCK DETECTION (Shipping label aware)
# =============================================================================

def run_address_name(lines, W, H) -> List[Detection]:
    """
    Detects address blocks and person names on shipping labels.
    Works with 2+ consecutive anchor lines (relaxed from 3).
    """
    dets = []
    sl = sorted(lines, key=lambda ln: bbox4(ln[0])[1])  # sort by Y (top to bottom)

    active = False
    bboxes, texts, ax = [], [], -1

    for line in sl:
        box, (t, _) = line
        ts = str(t).strip()
        if not ts:
            continue
        tl = ts.lower()
        x0, y0, x1, y1 = bbox4(box)
        words_set = set(re.split(r"\W+", tl))
        has_anchor = bool(words_set & ADDRESS_ANCHORS)
        has_pin = bool(_RE_PINCODE.search(ts))
        has_phone = bool(_RE_MOBILE.search(ts))

        if (has_anchor or has_pin or has_phone) and not active:
            active = True
            ax = x0
            bboxes = [(x0, y0, x1, y1)]
            texts = [ts]
        elif active:
            if abs(x0 - ax) < W * 0.50:  # relaxed alignment threshold
                bboxes.append((x0, y0, x1, y1))
                texts.append(ts)
            if has_pin or has_phone or len(bboxes) >= 5:
                # End of address block
                if len(bboxes) >= 2:
                    mx0 = min(b[0] for b in bboxes)
                    my0 = min(b[1] for b in bboxes)
                    mx1 = max(b[2] for b in bboxes)
                    my1 = max(b[3] for b in bboxes)
                    full = " | ".join(texts)
                    dets.append(make_det(
                        "address", "Address Block", full, 88.0,
                        mx0 - 5, my0 - 5, mx1 + 5, my1 + 5,
                        W, H, source="address_rules"
                    ))
                    print(f"  [Address] Found block: {full[:80]}")
                active, bboxes, texts, ax = False, [], [], -1

    # Flush any remaining block
    if active and len(bboxes) >= 2:
        mx0 = min(b[0] for b in bboxes)
        my0 = min(b[1] for b in bboxes)
        mx1 = max(b[2] for b in bboxes)
        my1 = max(b[3] for b in bboxes)
        full = " | ".join(texts)
        dets.append(make_det(
            "address", "Address Block", full, 88.0,
            mx0 - 5, my0 - 5, mx1 + 5, my1 + 5,
            W, H, source="address_rules"
        ))
        print(f"  [Address] Found block (flush): {full[:80]}")

    print(f"[Address] Total: {len(dets)} address blocks")
    return dets

# =============================================================================
# LAYER 4 -- WHOLE-TEXT SCAN (catches split OCR tokens)
# =============================================================================

def run_fulltext_scan(lines, W, H) -> List[Detection]:
    """
    Join all OCR text into one string, run patterns across the whole doc.
    Catches identifiers split across multiple OCR boxes.
    """
    dets = []
    seen = set()

    # Build word list with positions
    words = []
    full_text = ""
    for line in lines:
        box, (t, c) = line
        ts = str(t).strip()
        if not ts:
            continue
        x0, y0, x1, y1 = bbox4(box)
        for w in ts.split():
            s = len(full_text)
            full_text += w
            e = len(full_text)
            full_text += " "
            words.append((w, x0, y0, x1, y1, s, e))

    if not full_text.strip():
        return dets

    patterns = [
        ("aadhaar",  "Aadhaar Number",  _RE_AADHAAR, 95.0),
        ("phone",    "Mobile Number",   _RE_MOBILE,  91.0),
        ("pan",      "PAN Number",      _RE_PAN,     96.0),
        ("email",    "Email Address",   _RE_EMAIL,   92.0),
        ("pincode",  "PIN Code",        _RE_PINCODE, 80.0),
        ("tracking", "Tracking Number", _RE_TRACKING, 78.0),
    ]

    for type_str, label, pat, conf in patterns:
        for m in pat.finditer(full_text):
            mt = m.group(0).strip()
            key = f"{type_str}:{mt}"
            if key in seen or len(mt) < 5:
                continue
            # Skip short tracking numbers unless they look like a real code
            if type_str == "tracking" and len(mt) < 12:
                continue
            seen.add(key)

            es, ee = m.start(), m.end()
            ov = [w for w in words if not (w[6] <= es or w[5] >= ee)]
            if not ov:
                continue

            mx0 = min(w[1] for w in ov)
            my0 = min(w[2] for w in ov)
            mx1 = max(w[3] for w in ov)
            my1 = max(w[4] for w in ov)

            dets.append(make_det(type_str, label, mt, conf, mx0, my0, mx1, my1, W, H, source="fulltext_scan"))
            print(f"  [FullText] Found {label}: '{mt}'")

    print(f"[FullText] Total: {len(dets)} additional matches")
    return dets

# =============================================================================
# LAYER 5 -- FACE DETECTION (multi-method with profile support)
# =============================================================================

_HAAR_FRONTAL = None
_HAAR_PROFILE = None

def _get_haar_cascades():
    global _HAAR_FRONTAL, _HAAR_PROFILE
    if _HAAR_FRONTAL is None:
        _HAAR_FRONTAL = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        _HAAR_PROFILE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
    return _HAAR_FRONTAL, _HAAR_PROFILE

def _haar_detect(img, W, H) -> List[Detection]:
    """Detect frontal + profile faces with Haar cascades."""
    dets = []
    frontal_cc, profile_cc = _get_haar_cascades()
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray_eq = cv2.equalizeHist(gray)

    for cascade, label_suffix, conf in [
        (frontal_cc, "frontal", 78.0),
        (profile_cc, "profile", 72.0),
    ]:
        faces = cascade.detectMultiScale(
            gray_eq, scaleFactor=1.05, minNeighbors=4, minSize=(25, 25)
        )
        for i, (x, y, fw, fh) in enumerate(faces if len(faces) else []):
            dets.append(make_det(
                "face", "Face", "[FACE]", conf,
                x, y, x + fw, y + fh, W, H,
                uid=f"haar-{label_suffix}-{i}", source=f"haar_{label_suffix}"
            ))

    # Also try flipped image for left-profile faces
    flipped = cv2.flip(img, 1)
    gray_f = cv2.cvtColor(flipped, cv2.COLOR_BGR2GRAY)
    gray_feq = cv2.equalizeHist(gray_f)
    faces_flip = profile_cc.detectMultiScale(
        gray_feq, scaleFactor=1.05, minNeighbors=4, minSize=(25, 25)
    )
    for i, (x, y, fw, fh) in enumerate(faces_flip if len(faces_flip) else []):
        # Flip x coordinate back
        x_orig = W - x - fw
        dets.append(make_det(
            "face", "Face", "[FACE]", 70.0,
            x_orig, y, x_orig + fw, y + fh, W, H,
            uid=f"haar-lprofile-{i}", source="haar_profile_flip"
        ))

    print(f"[Haar] {len(dets)} face(s) (frontal+profile)")
    return dets

def run_faces(img, W, H) -> List[Detection]:
    dets = []

    # 1. InsightFace (best for frontal faces, Aadhaar-style)
    fa = get_insight_app()
    if fa != "unavailable" and fa is not None:
        try:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            faces = fa.get(img_rgb)
            for i, face in enumerate(faces):
                bb = face.bbox.astype(int)
                if bb[2] <= bb[0] or bb[3] <= bb[1]:
                    continue
                conf = float(face.det_score) * 100 if hasattr(face, "det_score") else 85.0
                dets.append(make_det(
                    "face", "Face", "[FACE]", conf,
                    max(0, bb[0]), max(0, bb[1]), min(W, bb[2]), min(H, bb[3]),
                    W, H, uid=f"iface-{i}", source="insightface"
                ))
            print(f"[InsightFace] {len(dets)} face(s)")
        except Exception as e:
            print(f"[InsightFace] Error: {e}")

    # 2. MediaPipe v0.10 new Tasks API (good for profile/side faces)
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        import urllib.request, os, tempfile

        model_path = os.path.join(tempfile.gettempdir(), "blaze_face_short_range.tflite")
        if not os.path.exists(model_path):
            url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"
            try:
                urllib.request.urlretrieve(url, model_path)
            except Exception:
                model_path = None

        if model_path and os.path.exists(model_path):
            base_opts = mp_python.BaseOptions(model_asset_path=model_path)
            opts = mp_vision.FaceDetectorOptions(base_options=base_opts, min_detection_confidence=0.5)
            with mp_vision.FaceDetector.create_from_options(opts) as detector:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
                result = detector.detect(mp_img)
                for i, det in enumerate(result.detections):
                    bb = det.bounding_box
                    x0p = max(0.0, bb.origin_x / W * 100)
                    y0p = max(0.0, bb.origin_y / H * 100)
                    x1p = min(100.0, (bb.origin_x + bb.width) / W * 100)
                    y1p = min(100.0, (bb.origin_y + bb.height) / H * 100)
                    conf = det.categories[0].score * 100 if det.categories else 75.0
                    d = Detection(
                        id=f"mp2-{i}", type="face", label="Face",
                        text="[FACE]", confidence=conf,
                        bbox=BoundingBox(x0=x0p, y0=y0p, x1=x1p, y1=y1p),
                        redacted=True, source="mediapipe_v2"
                    )
                    dets.append(d)
                if result.detections:
                    print(f"[MediaPipe v2] {len(result.detections)} face(s)")
    except Exception as e:
        print(f"[MediaPipe v2] Error: {e}")

    # 3. Haar cascade fallback (ALWAYS run - catches profiles InsightFace misses)
    # Disabled Haar cascades due to severe false positives on text/textures.
    # haar_dets = _haar_detect(img, W, H)
    # # Add Haar faces only if they don't overlap with existing detections
    # for hd in haar_dets:
    #     already_covered = any(
    #         iou(hd.bbox, existing.bbox) > 0.3
    #         for existing in dets
    #         if existing.type == "face"
    #     )
    #     if not already_covered:
    #         dets.append(hd)

    print(f"[Faces] Total: {len(dets)} face(s)")
    return dets

# =============================================================================
# LAYER 6 -- QR / BARCODE
# =============================================================================

def run_qr(img, W, H) -> List[Detection]:
    dets = []
    try:
        from pyzbar.pyzbar import decode as pyzbar_decode
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        codes = pyzbar_decode(gray)
        for i, code in enumerate(codes):
            r = code.rect
            ct = str(code.type).lower()
            tstr = "qr_code" if "qr" in ct else "barcode"
            label = "QR Code" if "qr" in ct else "Barcode"
            text = code.data.decode("utf-8", errors="replace")[:100] if code.data else ""
            dets.append(make_det(tstr, label, text, 95.0,
                                 r.left, r.top, r.left + r.width, r.top + r.height,
                                 W, H, uid=f"{tstr}-{i}", source="pyzbar"))
            print(f"  [QR/Barcode] Found {label}: {text[:40]}")
    except ImportError:
        # OpenCV fallback
        try:
            qrd = cv2.QRCodeDetector()
            data, pts, _ = qrd.detectAndDecode(img)
            if pts is not None and data:
                xs = [p[0] for p in pts[0]]
                ys = [p[1] for p in pts[0]]
                dets.append(make_det("qr_code", "QR Code", data[:100], 90.0,
                                     min(xs), min(ys), max(xs), max(ys), W, H, uid="qr-0", source="opencv_qr"))
        except Exception:
            pass
    except Exception as e:
        print(f"[QR] Error: {e}")

    print(f"[QR/Barcode] Total: {len(dets)}")
    return dets

# =============================================================================
# LAYER 7 -- YOLO OBJECT DETECTION (weapons, people, vehicles, license plates)
# =============================================================================

# COCO classes that are privacy/safety sensitive
_YOLO_PERSON_CLASS = 0
# Weapons/dangerous: knife=43, scissors=76 (scissors rarely, but included)
_YOLO_WEAPON_CLASSES = {43: "Knife", 76: "Scissors"}
# Vehicles (for license plate context)
_YOLO_VEHICLE_CLASSES = {2: "Car", 3: "Motorcycle", 5: "Bus", 7: "Truck"}

def run_yolo(img, W, H) -> List[Detection]:
    """Run YOLOv8n for person/weapon/vehicle detection."""
    dets = []
    yolo = get_yolo()
    if yolo == "unavailable" or yolo is None:
        return dets

    try:
        results = yolo.predict(img, conf=0.35, verbose=False)
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0]) * 100
                xyxy = box.xyxy[0].cpu().numpy()
                x0, y0, x1, y1 = float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])

                if cls_id == _YOLO_PERSON_CLASS:
                    # Person detected -> always blur (privacy)
                    dets.append(make_det(
                        "face", "Person", "[PERSON]", conf,
                        x0, y0, x1, y1, W, H,
                        uid=f"yolo-person-{len(dets)}", source="yolo_person"
                    ))
                    print(f"  [YOLO] Person at ({x0:.0f},{y0:.0f}) conf={conf:.0f}%")

                elif cls_id in _YOLO_WEAPON_CLASSES:
                    label = _YOLO_WEAPON_CLASSES[cls_id]
                    dets.append(make_det(
                        "weapon", label, f"[{label.upper()}]", conf,
                        x0, y0, x1, y1, W, H,
                        uid=f"yolo-weapon-{len(dets)}", source="yolo_weapon"
                    ))
                    print(f"  [YOLO] {label} detected conf={conf:.0f}%")

                elif cls_id in _YOLO_VEHICLE_CLASSES:
                    label = _YOLO_VEHICLE_CLASSES[cls_id]
                    # Vehicles don't themselves need blur, but flag for license plate extraction
                    dets.append(make_det(
                        "vehicle", label, f"[{label.upper()}]", conf,
                        x0, y0, x1, y1, W, H,
                        uid=f"yolo-vehicle-{len(dets)}", source="yolo_vehicle",
                        force_redact=False
                    ))
                    print(f"  [YOLO] {label} detected conf={conf:.0f}%")

        print(f"[YOLO] {len(dets)} object(s) detected")
    except Exception as e:
        print(f"[YOLO] Error: {e}")

    return dets

# =============================================================================
# LAYER 8 -- NUDENET (NSFW / Exposed Body Part Detection)
# =============================================================================

# Classes we ALWAYS redact (exposed intimate parts)
_NSFW_ALWAYS_BLUR = {
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "BUTTOCKS_EXPOSED",
    "ANUS_EXPOSED",
}
# Classes we redact only at high confidence
_NSFW_HIGH_CONF = {
    "BELLY_EXPOSED",
    "ARMPITS_EXPOSED",
    "FEMALE_BREAST_COVERED",
}
_NSFW_CONF_THRESHOLD   = 0.35   # primary threshold (lowered for better recall)
_NSFW_HIGH_CONF_THRESH = 0.55   # threshold for secondary classes (lowered for better recall)

# Human-readable labels
_NSFW_LABELS = {
    "FEMALE_BREAST_EXPOSED":    "Female Breast (Exposed)",
    "FEMALE_BREAST_COVERED":    "Female Breast (Covered)",
    "FEMALE_GENITALIA_EXPOSED": "Female Genitalia",
    "MALE_GENITALIA_EXPOSED":   "Male Genitalia",
    "BUTTOCKS_EXPOSED":         "Buttocks (Exposed)",
    "ANUS_EXPOSED":             "Anus",
    "BELLY_EXPOSED":            "Abdomen Exposed",
    "ARMPITS_EXPOSED":          "Armpit",
    "FEET_EXPOSED":             "Feet",
    "FACE_FEMALE":              "Female Face",
    "FACE_MALE":                "Male Face",
    "FACE_F":                   "Face",
    "FACE_M":                   "Face",
}

def run_nudenet(img, W, H) -> List[Detection]:
    """Run NudeNet to detect NSFW / exposed body parts."""
    dets = []
    nd = get_nudenet()
    if nd == "unavailable" or nd is None:
        return dets

    try:
        import tempfile, os
        # NudeNet requires a file path, write a temp image
        tmp_path = os.path.join(tempfile.gettempdir(), "_pg_nudenet_tmp.jpg")
        cv2.imwrite(tmp_path, img)
        results = nd.detect(tmp_path)

        for i, det in enumerate(results):
            cls   = det.get("class", "")
            score = float(det.get("score", 0.0))
            box   = det.get("box", [])

            # Decide whether to blur
            if cls in _NSFW_ALWAYS_BLUR and score >= _NSFW_CONF_THRESHOLD:
                should_blur = True
            elif cls in _NSFW_HIGH_CONF and score >= _NSFW_HIGH_CONF_THRESH:
                should_blur = True
            else:
                should_blur = False

            if not should_blur:
                continue

            if len(box) == 4:
                x0, y0, x1, y1 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
            else:
                continue

            label = _NSFW_LABELS.get(cls, cls.replace("_", " ").title())
            d = make_det(
                "nsfw", label, f"[NSFW:{cls}]", score * 100,
                x0, y0, x1, y1, W, H,
                uid=f"nudenet-{i}", source="nudenet", force_redact=True
            )
            dets.append(d)
            print(f"  [NudeNet] {label} conf={score:.2f} -> BLUR")

        print(f"[NudeNet] {len(dets)} NSFW region(s) flagged")
    except Exception as e:
        print(f"[NudeNet] Error: {e}")

    return dets

# =============================================================================
# LAYER 9 -- fast-alpr (License Plate Detector + OCR)
# =============================================================================

def run_alpr(img, W, H) -> List[Detection]:
    """Detect license plates using fast-alpr ONNX detector."""
    dets = []
    alpr = get_alpr()
    if alpr == "unavailable" or alpr is None:
        return dets

    try:
        import tempfile, os
        tmp_path = os.path.join(tempfile.gettempdir(), "_pg_alpr_tmp.jpg")
        cv2.imwrite(tmp_path, img)
        results = alpr.run(tmp_path)
        for i, plate in enumerate(results):
            bb   = plate.detection.bounding_box    # x, y, width, height (pixels)
            conf = float(plate.detection.confidence) * 100
            text = plate.ocr.text if plate.ocr else ""
            x0 = float(bb.x)
            y0 = float(bb.y)
            x1 = float(bb.x + bb.width)
            y1 = float(bb.y + bb.height)
            d = make_det(
                "license_plate", "License Plate", text or "[PLATE]", conf,
                x0, y0, x1, y1, W, H,
                uid=f"alpr-{i}", source="fast_alpr", force_redact=True
            )
            dets.append(d)
            print(f"  [ALPR] Plate '{text}' conf={conf:.0f}%")

        print(f"[ALPR] {len(dets)} plate(s) detected")
    except Exception as e:
        print(f"[ALPR] Error: {e}")

    return dets

# =============================================================================
# LAYER 10 -- SIGNATURE DETECTION (heuristic, handwriting zones)
# =============================================================================

def run_signatures(img, W, H, ocr_lines) -> List[Detection]:
    """
    Heuristic: Find isolated, near-horizontal ink strokes that look like
    handwritten signatures (low pixel density, curvy, not matching OCR text).
    """
    dets = []
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # Get OCR bounding boxes so we don't double-detect printed text
        ocr_boxes = []
        for line in ocr_lines:
            box, _ = line
            x0, y0, x1, y1 = bbox4(box)
            ocr_boxes.append((x0, y0, x1, y1))

        # Find connected components
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
        for lbl in range(1, num_labels):
            x  = int(stats[lbl, cv2.CC_STAT_LEFT])
            y  = int(stats[lbl, cv2.CC_STAT_TOP])
            cw = int(stats[lbl, cv2.CC_STAT_WIDTH])
            ch = int(stats[lbl, cv2.CC_STAT_HEIGHT])
            area = int(stats[lbl, cv2.CC_STAT_AREA])

            # Signatures are wide (aspect > 2.5) and not too tall (< 15% H)
            if cw < 80 or ch > H * 0.15 or cw < ch * 2.5:
                continue
            # Density < 0.25 (not a solid block of ink)
            density = area / (cw * ch)
            if density > 0.30 or density < 0.02:
                continue
            # Must not overlap heavily with printed OCR text
            x1b, y1b = x + cw, y + ch
            overlaps_ocr = any(
                max(0, min(x1b, ox1) - max(x, ox0)) * max(0, min(y1b, oy1) - max(y, oy0)) > (cw * ch * 0.5)
                for (ox0, oy0, ox1, oy1) in ocr_boxes
            )
            if overlaps_ocr:
                continue

            dets.append(make_det(
                "signature", "Signature", "[SIGNATURE]", 75.0,
                x - 4, y - 4, x1b + 4, y1b + 4, W, H,
                uid=f"sig-{lbl}", source="signature_heuristic"
            ))
            print(f"  [Signature] Detected region ({x},{y}) {cw}x{ch}")

        print(f"[Signature] {len(dets)} signature zone(s)")
    except Exception as e:
        print(f"[Signature] Error: {e}")

    return dets

# =============================================================================
# LAYER 11 -- DOCUMENT KEYWORD CLASSIFIER (medical, legal, financial docs)
# =============================================================================

# Keywords that indicate a sensitive document type
_DOC_KEYWORDS = {
    "medical": [
        "prescription", "rx", "diagnosis", "patient", "hospital", "clinic",
        "doctor", "dr.", "medicine", "dosage", "tablet", "capsule", "syrup",
        "blood", "report", "lab", "pathology", "mg", "ml", "injection",
        "insurance", "policy", "claim", "discharge",
    ],
    "legal": [
        "affidavit", "court", "judgement", "order", "plaintiff", "defendant",
        "hereby", "whereas", "notary", "advocate", "law", "section", "clause",
        "agreement", "contract", "deed", "witness", "signed", "stamp",
    ],
    "financial": [
        "invoice", "receipt", "payment", "amount", "total", "balance",
        "tax", "gst", "cgst", "sgst", "igst", "pan", "tin", "salary",
        "bank", "account", "interest", "cheque", "credit", "debit",
    ],
}

def run_doc_classifier(lines, W, H) -> List[Detection]:
    """
    If OCR text contains doc-type keywords, flag the entire image region
    as a sensitive document and blur the keyword-containing line.
    """
    dets = []
    seen_types = set()

    for line in lines:
        box, (text, conf) = line
        tl = text.lower()
        x0, y0, x1, y1 = bbox4(box)
        words_in_line = set(re.split(r"\W+", tl))

        for doc_type, kws in _DOC_KEYWORDS.items():
            if doc_type in seen_types:
                continue
            matched_kws = [kw for kw in kws if kw in tl or kw.replace(".","") in words_in_line]
            if matched_kws:
                seen_types.add(doc_type)
                label = f"{doc_type.title()} Document"
                dets.append(make_det(
                    f"document_{doc_type}", label,
                    f"[{doc_type.upper()} DOC: {', '.join(matched_kws[:3])}]",
                    82.0, x0, y0, x1, y1, W, H,
                    uid=f"doc-{doc_type}-{len(dets)}", source="doc_classifier"
                ))
                print(f"  [DocClassifier] {label} keyword match: {matched_kws[:3]}")

    print(f"[DocClassifier] {len(dets)} document type(s) flagged")
    return dets

# =============================================================================
# HEALTH & SCAN ENDPOINTS
# =============================================================================

@app.get("/")
def health():
    paddle_status  = "ready" if (get_paddle_ocr() not in ["unavailable", None]) else "unavailable"
    easy_status    = "ready" if (get_easyocr()    not in ["unavailable", None]) else "unavailable"
    nudenet_status = "ready" if (_nudenet_classifier not in ["unavailable", None]) else "loading"
    alpr_status    = "ready" if (_alpr_detector      not in ["unavailable", None]) else "loading"
    yolo_status    = "ready" if (_yolo_model         not in ["unavailable", None]) else "unavailable"
    return {
        "status": "ok",
        "version": "v6",
        "message": "Privacy Guardian V6 — 11-Layer Multi-Model Pipeline",
        "models": {
            "paddleocr":      paddle_status,
            "easyocr":        easy_status,
            "insightface":    "ready" if (_insight_app not in ["unavailable", None]) else "unavailable",
            "yolo":           yolo_status,
            "nudenet":        nudenet_status,
            "fast_alpr":      alpr_status,
            "regex":          "active",
            "address_rules":  "active",
            "doc_classifier": "active",
            "signature":      "active",
        }
    }

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        if "input" in error:
            del error["input"]
        errors.append(error)
    return JSONResponse(status_code=422, content={"detail": errors})

@app.post("/scan", response_model=ScanResponse)
async def scan(req: ScanRequest):
    t0 = time.time()
    diagnostics = {}

    # -- Decode Image ---------------------------------------------------------
    try:
        b64 = req.imageBase64
        if "base64," in b64:
            b64 = b64.split("base64,", 1)[1]
        b64 += "=" * ((4 - len(b64) % 4) % 4)
        buf = np.frombuffer(base64.b64decode(b64), np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"imdecode returned None. Buffer size: {len(buf)}")

        # Resize to max 960px on the longest side for performance
        h, w = img.shape[:2]
        max_dim = 960
        if w > max_dim or h > max_dim:
            scale = max_dim / max(w, h)
            img = cv2.resize(img, (int(w * scale), int(h * scale)))

        H, W = img.shape[:2]
        print(f"[Scan] Image size: {W}x{H}")
    except Exception as e:
        raise HTTPException(400, f"Image decode error: {e}")

    try:
        # -- CONCURRENT MODEL EXECUTION --------------------------------------------
        import concurrent.futures
        t_ocr = time.time()
        
        # Preprocess for OCR: CLAHE for contrast enhancement
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        img_enhanced = cv2.cvtColor(clahe.apply(gray), cv2.COLOR_GRAY2BGR)

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            fut_ocr = executor.submit(run_ocr, img_enhanced)
            fut_face = executor.submit(run_faces, img, W, H)
            fut_qr = executor.submit(run_qr, img, W, H)
            fut_yolo = executor.submit(run_yolo, img, W, H)
            fut_nsfw = executor.submit(run_nudenet, img, W, H)
            fut_alpr = executor.submit(run_alpr, img, W, H)

            lines = fut_ocr.result()
            face_d = fut_face.result()
            qr_d = fut_qr.result()
            yolo_d = fut_yolo.result()
            nsfw_d = fut_nsfw.result()
            alpr_d = fut_alpr.result()

        ocr_ms = int((time.time() - t_ocr) * 1000)
        full_text = " ".join(str(ln[1][0]) for ln in lines if ln[1][0])
        diagnostics["OCR"] = f"✓ {len(lines)} lines, {len(full_text)} chars" if lines else "X 0 lines"

        # YOLO person detections: only add if no InsightFace/Haar face overlaps
        yolo_persons = [d for d in yolo_d if d.type == "face"]
        yolo_others  = [d for d in yolo_d if d.type != "face"]
        for yp in yolo_persons:
            if not any(iou(yp.bbox, fd.bbox) > 0.3 for fd in face_d):
                face_d.append(yp)

        diagnostics["YOLO"] = f"✓ {len(yolo_d)} objects" if yolo_d else "X 0 objects"
        diagnostics["Faces"] = f"✓ {len(face_d)} faces" if face_d else "X 0 faces"
        diagnostics["Barcode/QR"] = f"✓ {len(qr_d)} codes" if qr_d else "X 0 codes"
        diagnostics["NSFW"] = f"✓ {len(nsfw_d)} regions" if nsfw_d else "X 0 regions"
        
        # -- TEXT-DEPENDENT LAYERS ------------------------------------------------
        regex_d = run_regex(lines, W, H)
        diagnostics["Regex"] = f"✓ {len(regex_d)} matches" if regex_d else "X 0 matches"
        
        # Merge ALPR plates with regex-detected plates (deduplicate by IoU)
        for ap in alpr_d:
            if not any(iou(ap.bbox, rd.bbox) > 0.4 for rd in regex_d if rd.type == "license_plate"):
                regex_d.append(ap)
        diagnostics["ALPR"] = f"✓ {len(alpr_d)} plates" if alpr_d else "X 0 plates"
    
        addr_d = run_address_name(lines, W, H)
        diagnostics["Address"] = f"✓ {len(addr_d)} blocks" if addr_d else "X 0 blocks"
    
        ft_d = run_fulltext_scan(lines, W, H)
        diagnostics["FullText"] = f"✓ {len(ft_d)} matches" if ft_d else "X 0 matches"
    
        sig_d = run_signatures(img, W, H, lines)
        diagnostics["Signatures"] = f"✓ {len(sig_d)} signatures" if sig_d else "X 0 signatures"
    
        doc_d = run_doc_classifier(lines, W, H)
        diagnostics["Documents"] = f"✓ {len(doc_d)} doc types" if doc_d else "X 0 doc types"
    
        # -- Merge & NMS -----------------------------------------------------------
        all_dets = regex_d + addr_d + ft_d + face_d + qr_d + yolo_others + sig_d + doc_d + nsfw_d
    
        # Priority 1: NSFW always force-redact (already set in run_nudenet)
        # Priority 2: Weapons always redact
        for d in all_dets:
            if d.confidence >= 70.0:
                d.redacted = True
            if d.type in ("weapon", "nsfw"):
                d.redacted = True
    
        # NMS by category groups
        face_dets   = [d for d in all_dets if d.type == "face"]
        weapon_dets = [d for d in all_dets if d.type == "weapon"]
        nsfw_dets   = [d for d in all_dets if d.type == "nsfw"]   # never suppressed
        text_dets   = [d for d in all_dets if d.type not in ("face", "weapon", "nsfw")]
    
        merged = (
            nms(face_dets, thr=0.35)
            + weapon_dets
            + nsfw_dets
            + nms(text_dets, thr=0.7)
        )
    
        # Remove zero-area boxes and context-only vehicle boxes
        merged = [
            d for d in merged
            if (d.bbox.x1 - d.bbox.x0) > 0
            and (d.bbox.y1 - d.bbox.y0) > 0
            and d.type != "vehicle"
        ]
    
        diagnostics["Final"] = f"✓ {len(merged)} total detections"
    
        # -- Privacy Score ---------------------------------------------------------
        base_score = 100
        for d in merged:
            if d.type == "nsfw":
                base_score -= 35   # NSFW is highest risk
            elif d.type in ("face", "aadhaar", "pan"):
                base_score -= 20
            elif d.type in ("phone", "email"):
                base_score -= 15
            elif d.type == "address":
                base_score -= 18
            elif d.type == "weapon":
                base_score -= 25
            elif d.type == "license_plate":
                base_score -= 12
            elif d.type == "signature":
                base_score -= 10
            elif d.type.startswith("document_"):
                base_score -= 8
            else:
                base_score -= 5
        privacy_score = max(0, min(100, base_score))
    
        # -- Build OCR Words -------------------------------------------------------
        words_out = []
        for ln in lines:
            box, (t, c) = ln
            try:
                xs = [float(p[0]) for p in box]
                ys = [float(p[1]) for p in box]
                x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
                def pct(v, dim): return float(max(0.0, min(100.0, (v / dim) * 100.0)))
                words_out.append(OCRWord(
                    text=str(t), confidence=float(c),
                    bbox=BoundingBox(x0=pct(x0, W), y0=pct(y0, H), x1=pct(x1, W), y1=pct(y1, H))
                ))
            except Exception:
                pass
    
        # -- Metrics ---------------------------------------------------------------
        ms = int((time.time() - t0) * 1000)
        total_area = W * H
        redacted_area = sum(
            ((d.bbox.x1 - d.bbox.x0) / 100.0 * W) * ((d.bbox.y1 - d.bbox.y0) / 100.0 * H)
            for d in merged if d.redacted
        )
        coverage_pct = min(100.0, (redacted_area / total_area) * 100.0) if total_area > 0 else 0.0
        mem_mb = psutil.Process().memory_info().rss / (1024 * 1024)
    
        metrics = SystemMetrics(
            ocr_latency_ms=ocr_ms,
            total_latency_ms=ms,
            redaction_coverage_pct=round(coverage_pct, 2),
            memory_usage_mb=round(mem_mb, 2)
        )
    
        print(
            f"[Scan] DONE {ms}ms | {W}x{H} | "
            f"ocr={len(lines)} regex={len(regex_d)} addr={len(addr_d)} ft={len(ft_d)} "
            f"face={len(face_d)} qr={len(qr_d)} yolo={len(yolo_d)} "
            f"nsfw={len(nsfw_d)} alpr={alpr_plates} sig={len(sig_d)} doc={len(doc_d)} "
            f"-> merged={len(merged)} | privacy={privacy_score}"
        )
    
        return ScanResponse(
            detections=merged,
            words=words_out,
            fullText=full_text.strip(),
            processingTime=ms,
            aiDescription="",
            privacyScore=privacy_score,
            metrics=metrics,
            diagnostics=diagnostics
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        diagnostics["Pipeline_Error"] = str(e)
        return ScanResponse(
            detections=[], words=[], fullText="",
            processingTime=int((time.time() - t0) * 1000),
            aiDescription="", privacyScore=100,
            metrics=SystemMetrics(ocr_latency_ms=0, total_latency_ms=int((time.time() - t0) * 1000), redaction_coverage_pct=0.0, memory_usage_mb=0.0),
            diagnostics=diagnostics
        )

@app.post("/feedback")
async def receive_feedback(req: FeedbackRequest):
    import os
    out_dir = "dataset/active_learning"
    images_dir = os.path.join(out_dir, "images")
    labels_dir = os.path.join(out_dir, "labels")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)

    b64 = req.image
    if b64.startswith("data:image"):
        b64 = b64.split(",")[1]

    img_data = base64.b64decode(b64)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return {"status": "error", "message": "Invalid image"}

    H, W = img.shape[:2]
    file_id = f"feedback_{int(time.time() * 1000)}"
    img_path = os.path.join(images_dir, f"{file_id}.jpg")
    lbl_path = os.path.join(labels_dir, f"{file_id}.txt")
    cv2.imwrite(img_path, img)

    class_map = {"face": 0, "pan": 1, "logo": 2, "signature": 3, "text": 4}
    with open(lbl_path, "w") as f:
        for c in req.corrections:
            cls_id = class_map.get(c.type.lower(), 0)
            # bbox is already in x0/y0/x1/y1 percentage format
            x_c = (c.bbox.x0 + c.bbox.x1) / 2.0 / 100.0
            y_c = (c.bbox.y0 + c.bbox.y1) / 2.0 / 100.0
            w_n = (c.bbox.x1 - c.bbox.x0) / 100.0
            h_n = (c.bbox.y1 - c.bbox.y0) / 100.0
            f.write(f"{cls_id} {x_c:.6f} {y_c:.6f} {w_n:.6f} {h_n:.6f}\n")

    print(f"[Active Learning] Saved {len(req.corrections)} corrections to {out_dir}")
    return {"status": "success", "file_id": file_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
