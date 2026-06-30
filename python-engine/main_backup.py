import base64
import re
import time
import uuid as _uuid
from contextlib import asynccontextmanager
from typing import List, Optional
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
_yolo_model = None
_weapons_model = None   # guns, rifles, pistols — YOLOv8 weapons
_smoking_model = None   # cigarettes, vapes — YOLOv8 smoking
_plate_model   = None   # license plates — YOLOv8 plates

# COCO classes that are safety-sensitive → (type, label)
_YOLO_SAFETY_CLASSES = {
    # weapons
    43: ("illegal_item", "Knife / Weapon"),
    # alcohol / bottle — heuristic: any bottle at moderate confidence → flag
    39: ("illegal_item", "Alcohol Bottle"),
    74: ("illegal_item", "Bottle"),
    40: ("illegal_item", "Wine Glass"),
    41: ("illegal_item", "Cup / Drink"),
    # smoking / fire (limited COCO coverage)
    76: ("illegal_item", "Scissors"),
}

def get_ocr_model():
    global _ocr_model
    if _ocr_model is None:
        from paddleocr import PaddleOCR
        _ocr_model = PaddleOCR(use_angle_cls=False, lang="en", enable_mkldnn=False, cpu_threads=2)
        print("[OCR] PaddleOCR ready")
    return _ocr_model

def get_gliner_model():
    global _gliner_model
    if _gliner_model is None:
        try:
            from gliner import GLiNER
            _gliner_model = GLiNER.from_pretrained("knowledgator/gliner-pii-base-v1.0")
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
            # Lowered threshold (0.25) to catch faint ghost image faces
            app.prepare(ctx_id=-1, det_size=(1280, 1280), det_thresh=0.25)
            _insight_app = app
            print("[InsightFace] SCRFD ready — multi-face detection enabled (det_thresh=0.30)")
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

def get_yolo_model():
    global _yolo_model
    if _yolo_model is None:
        try:
            from ultralytics import YOLO
            _yolo_model = YOLO("yolov8n.pt")  # nano model – fast, small download
            print("[YOLO] YOLOv8n ready for safety detection")
        except Exception as e:
            print(f"[YOLO] Unavailable: {e}")
            _yolo_model = "unavailable"
    return _yolo_model

def get_weapons_model():
    """Dedicated YOLOv8 model fine-tuned on firearms & weapons."""
    global _weapons_model
    if _weapons_model is None:
        try:
            from ultralytics import YOLO
            from huggingface_hub import hf_hub_download
            pt = hf_hub_download(
                repo_id="keremberke/yolov8n-weapons-detection",
                filename="best.pt",
                repo_type="model",
            )
            _weapons_model = YOLO(pt)
            print("[Weapons] YOLOv8 weapons model ready")
        except Exception as e:
            print(f"[Weapons] Unavailable: {e}")
            _weapons_model = "unavailable"
    return _weapons_model

def run_weapons_detector(img, W, H):
    """Detect guns, rifles, pistols and return blur detections."""
    model = get_weapons_model()
    if model == "unavailable" or model is None:
        return []
    try:
        results = model(img, verbose=False, conf=0.30)[0]
        dets = []
        for box in results.boxes:
            cls_name = results.names[int(box.cls[0])].lower()
            conf = float(box.conf[0]) * 100
            x0, y0, x1, y1 = box.xyxy[0].tolist()
            label = cls_name.replace("-", " ").replace("_", " ").title()
            dets.append(make_det("illegal_item", label, label, conf, x0, y0, x1, y1, W, H, force_redact=True))
            print(f"[Weapons] Detected {label} ({conf:.1f}%)")
        return dets
    except Exception as e:
        print(f"[Weapons] Error: {e}")
        return []

def get_smoking_model():
    """Dedicated YOLOv8 model for cigarette / smoking detection."""
    global _smoking_model
    if _smoking_model is None:
        try:
            from ultralytics import YOLO
            from huggingface_hub import hf_hub_download
            pt = hf_hub_download(
                repo_id="MeetCool/yolov8n-smoking-detection",
                filename="models/fine_tune_YOLOv8n.pt",
                repo_type="model",
            )
            _smoking_model = YOLO(pt)
            print("[Smoking] YOLOv8 cigarette & smoking model ready")
        except Exception as e:
            print(f"[Smoking] Unavailable: {e}")
            _smoking_model = "unavailable"
    return _smoking_model

def run_smoking_detector(img, W, H):
    """Detect cigarettes, vapes, smoke and return blur detections."""
    model = get_smoking_model()
    if model == "unavailable" or model is None:
        return []
    try:
        # Confidence lowered aggressively to 0.10 to catch unlit or small cigarettes
        results = model(img, verbose=False, conf=0.10)[0]
        dets = []
        for box in results.boxes:
            cls_name = results.names[int(box.cls[0])].lower()
            # This model detects: 0: 'cigarette', 1: 'person', 2: 'smoke'
            # We ONLY want to redact the cigarette and smoke, not the whole person
            if cls_name == "person":
                continue
                
            conf = float(box.conf[0]) * 100
            x0, y0, x1, y1 = box.xyxy[0].tolist()
            
            # Add generous padding so the heavy blur completely covers the cigarette
            pad_x = (x1 - x0) * 0.20
            pad_y = (y1 - y0) * 0.20
            x0 = max(0, x0 - pad_x)
            y0 = max(0, y0 - pad_y)
            x1 = min(W, x1 + pad_x)
            y1 = min(H, y1 + pad_y)
            
            label = cls_name.replace("-", " ").replace("_", " ").title()
            dets.append(make_det("illegal_item", label, label, conf, x0, y0, x1, y1, W, H, force_redact=True))
            print(f"[Smoking] Detected {label} ({conf:.1f}%)")
        return dets
    except Exception as e:
        print(f"[Smoking] Error: {e}")
        return []

def get_plate_model():
    """Dedicated YOLOv8 license plate detection model."""
    global _plate_model
    if _plate_model is None:
        try:
            from ultralytics import YOLO
            from huggingface_hub import hf_hub_download
            pt = hf_hub_download(
                repo_id="keremberke/yolov8n-license-plate-detection",
                filename="best.pt",
                repo_type="model",
            )
            _plate_model = YOLO(pt)
            print("[Plates] YOLOv8 license plate model ready")
        except Exception as e:
            print(f"[Plates] Unavailable: {e}")
            _plate_model = "unavailable"
    return _plate_model

def run_plate_detector(img, W, H):
    """Detect license plates (vehicles, parking permits) and return blur detections."""
    model = get_plate_model()
    if model == "unavailable" or model is None:
        return []
    try:
        results = model(img, verbose=False, conf=0.35)[0]
        dets = []
        for box in results.boxes:
            conf = float(box.conf[0]) * 100
            x0, y0, x1, y1 = box.xyxy[0].tolist()
            dets.append(make_det("license_plate", "License Plate", "[PLATE]", conf, x0, y0, x1, y1, W, H, force_redact=True))
            print(f"[Plates] Detected license plate ({conf:.1f}%)")
        return dets
    except Exception as e:
        print(f"[Plates] Error: {e}")
        return []

def run_yolo_safety(img, W, H):
    """Detect safety-relevant visual objects (weapons, alcohol, etc.) using YOLO."""
    model = get_yolo_model()
    if model == "unavailable" or model is None:
        return []
    try:
        results = model(img, verbose=False, conf=0.35)[0]
        dets = []
        for box in results.boxes:
            cls_id = int(box.cls[0])
            if cls_id not in _YOLO_SAFETY_CLASSES:
                continue
            det_type, det_label = _YOLO_SAFETY_CLASSES[cls_id]
            conf = float(box.conf[0]) * 100
            x0, y0, x1, y1 = box.xyxy[0].tolist()
            # For alcohol bottles, require higher confidence to reduce false positives
            min_conf = 60 if cls_id in (39, 74, 40, 41) else 40
            if conf < min_conf:
                continue
            dets.append(make_det(det_type, det_label, det_label, conf, x0, y0, x1, y1, W, H, force_redact=True))
            print(f"[YOLO] Detected {det_label} ({conf:.1f}%) at [{x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}]")
        return dets
    except Exception as e:
        print(f"[YOLO] Detection error: {e}")
        return []

# ── NudeNet body part detection ───────────────────────────────────────────────
_nudenet_detector = None
_NUDENET_CLASSES_TO_BLUR = {
    # Explicit — highest priority
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "BUTTOCKS_EXPOSED",
    "ANUS_EXPOSED",
    # Covered but still sensitive
    "FEMALE_BREAST_COVERED",
    "FEMALE_GENITALIA_COVERED",
    "MALE_GENITALIA_COVERED",
    "BUTTOCKS_COVERED",
    # Belly / armpits in explicit context
    "BELLY_EXPOSED",
    "ARMPITS_EXPOSED",
}

def get_nudenet():
    global _nudenet_detector
    if _nudenet_detector is None:
        try:
            from nudenet import NudeDetector
            _nudenet_detector = NudeDetector()
            print("[NudeNet] Detector ready")
        except Exception as e:
            print(f"[NudeNet] Unavailable: {e}")
            _nudenet_detector = "unavailable"
    return _nudenet_detector

def run_nudenet(img, W, H):
    """Detect exposed private body parts and return blur detections."""
    detector = get_nudenet()
    if detector == "unavailable" or detector is None:
        return []
    try:
        import tempfile, os
        import cv2
        # NudeNet needs a file path — write to a temp file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name
        cv2.imwrite(tmp_path, img)
        results = detector.detect(tmp_path)
        os.unlink(tmp_path)

        dets = []
        for r in results:
            cls = r.get("class", "")
            if cls not in _NUDENET_CLASSES_TO_BLUR:
                continue
            score = float(r.get("score", 0)) * 100
            # Lower threshold: covered parts at 25+, exposed parts at 15+
            is_exposed = "EXPOSED" in cls
            min_score = 15.0 if is_exposed else 25.0
            if score < min_score:
                continue
            box = r.get("box", [])
            if len(box) < 4:
                continue
            x0, y0, bw, bh = box[0], box[1], box[2], box[3]
            # Add 8% padding around body-part boxes for better coverage
            pad_x = bw * 0.08
            pad_y = bh * 0.08
            x0 = max(0, x0 - pad_x)
            y0 = max(0, y0 - pad_y)
            bw = bw + pad_x * 2
            bh = bh + pad_y * 2
            x1, y1 = x0 + bw, y0 + bh
            label = cls.replace("_", " ").title()
            dets.append(make_det("nudity", label, label, score, x0, y0, x1, y1, W, H, force_redact=True))
            print(f"[NudeNet] Detected {label} ({score:.1f}%) at [{x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}]")
        return dets
    except Exception as e:
        print(f"[NudeNet] Detection error: {e}")
        return []


_llm_pipe = None

def get_llm_pipe():
    global _llm_pipe
    if _llm_pipe is None:
        try:
            import torch
            torch.set_num_threads(8)
            from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
            MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
            tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
            model = AutoModelForCausalLM.from_pretrained(
                MODEL_ID, torch_dtype=torch.bfloat16
            )
            # Use PyTorch 2.0 SDPA if possible
            if hasattr(torch.nn.functional, 'scaled_dot_product_attention'):
                model = model.to(memory_format=torch.channels_last)
            _llm_pipe = pipeline("text-generation", model=model, tokenizer=tokenizer, device="cpu")
            print("[LLM] Qwen pipeline ready")
        except Exception as e:
            print(f"[LLM] Unavailable: {e}")
            _llm_pipe = "unavailable"
    return _llm_pipe

def parse_json_from_text(text: str) -> dict:
    match = re.search(r'\{.*?\}', text, re.DOTALL)
    if match:
        try:
            import json
            return json.loads(match.group(0))
        except:
            pass
    return {}

def run_llm_extractor(full_text, lines, W, H):
    pipe = get_llm_pipe()
    if pipe == "unavailable" or pipe is None:
        return []
    if len(full_text) < 10:
        return []
    try:
        t0_llm = time.time()
        messages = [
            {"role": "system", "content": "You are a privacy auditor. Read the OCR text and write ONLY a 1-sentence summary of the vulnerable PII risk."},
            {"role": "user", "content": f"OCR Text:\n{full_text[:100]}"}
        ]
        prompt = pipe.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        outputs = pipe(prompt, max_new_tokens=25, temperature=0.1, top_p=0.9, do_sample=True, return_full_text=False)
        gen_text = outputs[0]["generated_text"].strip()
        
        # We don't parse JSON anymore, just use the raw text as ai_desc
        ai_desc = gen_text.replace("\n", " ").strip()
        print(f"[LLM] Generated desc in {time.time() - t0_llm:.2f}s: {ai_desc}")
        
        dets = []
        if ai_desc:
            dets.append(make_det("ai_desc", "AI", ai_desc, 100.0, 0, 0, W, H, W, H))
            
        return dets
    except Exception as e:
        print(f"[LLM] Error: {e}")
        return []

# -- FastAPI lifespan (pre-warm OCR at startup) -------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] Pre-warming models...")
    try:
        get_ocr_model()
        get_gliner_model()
        get_insight_app()
        get_nudenet()          # body part detection
        get_weapons_model()    # guns, rifles
        get_smoking_model()    # cigarettes
        get_plate_model()      # license plates
        get_llm_pipe()
    except Exception as e:
        print(f"[Startup] Warm-up failed: {e}")
    print("[Startup] Server ready")
    yield
    print("[Shutdown] Cleaning up")

app = FastAPI(title="Privacy Guardian - V4 Ultra-Accuracy Redaction Engine", lifespan=lifespan)

# -- Pydantic models ----------------------------------------------------------

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

class OCRWord(BaseModel):
    text: str
    confidence: float
    bbox: BoundingBox

class ScanResponse(BaseModel):
    detections: List[Detection]
    words: List[OCRWord]
    fullText: str
    processingTime: int
    aiDescription: str = ""
    privacyScore: int = 55

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

# ---- Bank Account — only detect via LABEL context (standalone 9-18 digit pattern
# is too noisy: it matches Aadhaar, phone parts, etc.)
# Detection happens in the label-context boost section of run_regex.
_BANK_ACCT = r"\b\d{9,18}\b"  # used ONLY with label context, not standalone

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
# NOTE: _BANK_ACCT is intentionally excluded — 9-18 digit standalone match
# is too noisy (matches Aadhaar, product codes, etc). Bank accounts are
# detected via label-context ("A/C:", "Account:") in run_regex instead.
REGEX_TABLE = [
    ("aadhaar",      "Aadhaar VID",      re.compile(_AADHAAR_VID,    re.I), 95),
    ("aadhaar",      "Aadhaar Number",   re.compile(_AADHAAR_PLAIN,  re.I), 93),
    ("aadhaar",      "Masked Aadhaar",   re.compile(_AADHAAR_MASKED, re.I), 88),
    ("pan",          "PAN Number",       re.compile(_PAN),                  96),
    ("phone",        "Mobile Number",    re.compile(_MOBILE),               91),
    ("email",        "Email Address",    re.compile(_EMAIL,          re.I), 92),
    ("bank_account", "IFSC Code",        re.compile(_IFSC),                 90),
    ("credit_card",  "Card Number",      re.compile(_CARD),                 85),
    ("passport",     "Passport Number",  re.compile(_PASSPORT),             87),
    ("voter_id",     "Voter ID",         re.compile(_VOTER_ID),             84),
    ("gstin",        "GSTIN",            re.compile(_GSTIN),                92),
    ("upi",          "UPI ID",           re.compile(_UPI,            re.I), 68),  # lowered: @-text is noisy
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
    "receiver", "sender", "to", "from", "jalan", "jln", "taman", "lorong", "bukit", "kampung"
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# -- Verhoeff Checksum for Aadhaar --
_verhoeff_d = (
    (0,1,2,3,4,5,6,7,8,9),
    (1,2,3,4,0,6,7,8,9,5),
    (2,3,4,0,1,7,8,9,5,6),
    (3,4,0,1,2,8,9,5,6,7),
    (4,0,1,2,3,9,5,6,7,8),
    (5,9,8,7,6,0,4,3,2,1),
    (6,5,9,8,7,1,0,4,3,2),
    (7,6,5,9,8,2,1,0,4,3),
    (8,7,6,5,9,3,2,1,0,4),
    (9,8,7,6,5,4,3,2,1,0)
)
_verhoeff_p = (
    (0,1,2,3,4,5,6,7,8,9),
    (1,5,7,6,2,8,3,0,9,4),
    (5,8,0,3,7,9,6,1,4,2),
    (8,9,1,6,0,4,3,5,2,7),
    (9,4,5,3,1,2,6,8,7,0),
    (4,2,8,6,5,7,3,9,0,1),
    (2,7,9,3,8,0,6,4,1,5),
    (7,0,4,6,9,1,3,2,5,8)
)

def is_valid_aadhaar_verhoeff(num_str: str) -> bool:
    digits = [int(c) for c in num_str if c.isdigit()]
    if len(digits) != 12:
        return False
    digits.reverse()
    c = 0
    for i, d in enumerate(digits):
        c = _verhoeff_d[c][_verhoeff_p[i % 8][d]]
    return c == 0

# -- Face Landmark Geometry Validation --
def validate_face_landmarks(kps):
    # kps is typically shape (5, 2):
    # 0: left eye, 1: right eye, 2: nose, 3: left mouth, 4: right mouth
    if len(kps) < 5:
        return False
    le, re, nose, lm, rm = kps[0], kps[1], kps[2], kps[3], kps[4]
    
    # Check if eyes are above mouth (smaller y value means higher up in image)
    eyes_y = (le[1] + re[1]) / 2.0
    mouth_y = (lm[1] + rm[1]) / 2.0
    
    # Nose should generally be between eyes and mouth vertically
    if not (eyes_y < nose[1] < mouth_y):
        # Allow some margin for tilted faces, but strict inversion implies false positive
        if nose[1] < eyes_y - 20 or nose[1] > mouth_y + 20:
            return False
            
    # Eyes should be above mouth
    if eyes_y > mouth_y:
        return False
        
    return True


# Industry-grade confidence tiers (matching Google DLP / AWS Rekognition approach):
# ≥78% → AUTO-REDACT (high confidence, shown as blur layer)
# 55–78% → SUGGEST (highlighted but not auto-blurred, user decides)
# <55% → DISCARD (noise, not sent to frontend)
_AUTO_REDACT_THRESHOLD = 70.0
_SUGGEST_THRESHOLD     = 45.0   # matches Google DLP "POSSIBLE" tier

# Face detections always auto-redact at any confidence (they're never suggestions)
_FACE_MIN_CONFIDENCE   = 60.0

def make_det(type_str, label, text, conf, x0, y0, x1, y1, W, H, uid=None, force_redact=False):
    uid = uid or f"{type_str}-{_uuid.uuid4().hex[:8]}"
    def pct(v, dim): return float(max(0.0, min(100.0, (v / dim) * 100)))
    # Auto-redact everything above the threshold (70%)
    auto = force_redact or (conf >= _AUTO_REDACT_THRESHOLD)

    return Detection(
        id=uid, type=type_str, label=label, text=str(text)[:200],
        confidence=float(conf),
        bbox=BoundingBox(x0=pct(x0, W), y0=pct(y0, H), x1=pct(x1, W), y1=pct(y1, H)),
        redacted=auto,
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
                # Relaxed Verhoeff checksum to catch noisy OCR matches
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
    "city", "state", "district",
    "pin code", "postal code", "zip code",
]

GLINER_TYPE_MAP = {
    "person": "name", "person name": "name", "full name": "name", "individual": "name",
    "address": "address", "street address": "address", "residential address": "address",
    "mailing address": "address", "city": "address", "state": "address",
    "district": "address",
    "pin code": "pincode", "postal code": "pincode", "zip code": "pincode",
}

# Blocklist: text that must NEVER be redacted (government/institution boilerplate)
_NER_BLOCKLIST = {
    "government of india", "govt of india", "भारत सरकार", "india",
    "unique identification authority of india", "uidai",
    "income tax department",
    "reserve bank of india", "rbi",
    "aadhaar", "आधार", "pan card", "aadhar",
    "male", "female", "पुरुष", "महिला",
    "aadhaar is proof of identity", "proof of identity",
    "not of citizenship", "not of citezenship",
    "mera aadhaar meri pehchaan", "मेरा आधार मेरी पहचान",
}

# =============================================================================
# LAYER 2.5 — MULTI-BOX REGEX ENGINE (For split text like License Plates)
# =============================================================================

def run_multi_box_regex(lines, W, H) -> List[Detection]:
    words = []
    text = ""
    for line in lines:
        box, (t, c) = line
        ts = str(t).strip()
        if not ts: continue
        x0, y0, x1, y1 = bbox4(box)
        for w in ts.split():
            s = len(text)
            text += w
            e = len(text)
            text += " "
            words.append((w, x0, y0, x1, y1, s, e))
    
    if not text:
        return []

    dets = []
    seen = set()
    
    patterns = [
        # License plates
        ("license_plate", "License Plate",  re.compile(r"\b[A-Z]{2}[ .\-]?\d{1,2}[ .\-]?([A-Z]{1,3})?[ .\-]?\d{4}\b", re.I), 92.0),
        ("license_plate", "BH Series Plate", re.compile(r"\b\d{2}[ .\-]?BH[ .\-]?\d{4}[ .\-]?[A-Z]{1,2}\b", re.I), 94.0),
        # Aadhaar — 12-digit number (split across OCR tokens: "4906 5637 6032")
        ("aadhaar", "Aadhaar Number", re.compile(r"\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}\b"), 95.0),
        # Aadhaar VID — 16-digit
        ("aadhaar", "Aadhaar VID",    re.compile(r"\b[2-9]\d{3}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"), 97.0),
        # PAN card — ABCDE1234F
        ("pan",     "PAN Number",     re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), 96.0),
        # Mobile number
        ("phone",   "Mobile Number",  re.compile(r"\b(?:\+91[\s\-]?)?[6-9]\d{9}\b"), 91.0),
        # Passport — A1234567
        ("passport","Passport Number",re.compile(r"\b[A-Z]\d{7}\b"), 87.0),
        # Voter ID — ABC1234567
        ("voter_id","Voter ID",       re.compile(r"\b[A-Z]{3}\d{7}\b"), 84.0),
        # Credit/Debit card — 16 digits
        ("credit_card","Card Number", re.compile(r"\b\d{4}[\s\-]\d{4}[\s\-]\d{4}[\s\-]\d{4}\b"), 90.0),
    ]
    
    for type_str, label, pat, conf in patterns:
        for m in pat.finditer(text):
            mt = m.group(0).strip()
            es, ee = m.start(), m.end()
            key = f"{type_str}:{mt}"
            if key in seen: continue
            seen.add(key)
            
            ov = [w for w in words if not (w[6] <= es or w[5] >= ee)]
            if not ov: continue
            
            mx0 = min(w[1] for w in ov)
            my0 = min(w[2] for w in ov)
            mx1 = max(w[3] for w in ov)
            my1 = max(w[4] for w in ov)
            
            dets.append(make_det(
                type_str, label, mt, conf,
                mx0, my0, mx1, my1, W, H
            ))
            
    return dets

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
        # Lower threshold to 0.45 to catch more names (previously 0.72)
        ents = model.predict_entities(text, GLINER_LABELS, threshold=0.45)
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

        # Skip blocklisted government / boilerplate text
        etext_l = etext.strip().lower()
        if etext_l in _NER_BLOCKLIST:
            print(f"[GLiNER] Skipping blocklisted entity: '{etext}'")
            continue
        # Also skip if any blocklist phrase contains/is contained by this entity
        if any(bl in etext_l or etext_l in bl for bl in _NER_BLOCKLIST if len(bl) > 3):
            print(f"[GLiNER] Skipping near-match blocklisted entity: '{etext}'")
            continue
        # Skip very short tokens (2 chars or less) - high false positive rate
        if len(etext_l) <= 2:
            continue

        key = f"{etype}:{etext_l}"
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
        anchor  = bool(words_set & ADDRESS_ANCHORS) or bool(re.search(r"\bno\.\s*\d+", tl))
        has_pin = bool(re.search(r"\b\d{5,6}\b", ts))

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

    if active and len(bboxes) >= 3:   # ≥3 lines required (was 2) — reduces false positives
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

def run_insightface(img, W, H, trusted_faces_b64: Optional[List[str]] = None):
    """Run InsightFace with multi-scale detection and skip trusted faces."""
    fa = get_insight_app()
    if fa == "unavailable" or fa is None:
        return [], 0
    try:
        # 1. Get Trusted Face Embeddings
        ref_embeddings = []
        if trusted_faces_b64:
            for b64 in trusted_faces_b64:
                try:
                    if "base64," in b64:
                        b64 = b64.split("base64,", 1)[1]
                    t_buf = np.frombuffer(base64.b64decode(b64), np.uint8)
                    t_img = cv2.imdecode(t_buf, cv2.IMREAD_COLOR)
                    if t_img is not None:
                        t_rgb = cv2.cvtColor(t_img, cv2.COLOR_BGR2RGB)
                        t_faces = fa.get(t_rgb)
                        if t_faces:
                            # Use the largest face if multiple
                            t_faces = sorted(t_faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]), reverse=True)
                            ref_embeddings.append(t_faces[0].normed_embedding)
                        else:
                            print(f"[InsightFace] Trusted face {b64[:15]}... had NO faces detected in it.")
                except Exception as e:
                    print(f"[InsightFace] Error processing trusted face: {e}")
        print(f"[InsightFace] Extracted {len(ref_embeddings)} reference embeddings from {len(trusted_faces_b64 or [])} inputs.")

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        all_faces = []

        # Pass 1: full resolution (catches normal-size faces)
        all_faces = fa.get(img_rgb)

        dets = []
        seen_boxes = []
        valid_faces_count = 0
        for i, face in enumerate(all_faces):
            bb   = face.bbox.astype(int)
            conf = float(face.det_score) * 100 if hasattr(face, "det_score") else 85.0
            
            # Skip invalid boxes or faces without landmarks (reduces false positives)
            if bb[2] <= bb[0] or bb[3] <= bb[1]:
                continue
            if getattr(face, "kps", None) is None or len(face.kps) < 5:
                continue
            
            # Dynamic landmark bypass: small ghost images have noisy landmarks
            face_width = bb[2] - bb[0]
            is_small_face = face_width < (W * 0.15)
            if not is_small_face and not validate_face_landmarks(face.kps):
                continue
            
            valid_faces_count += 1
            # Deduplicate: skip if already have a box with >50% overlap
            new_box = (max(0,bb[0]), max(0,bb[1]), min(W,bb[2]), min(H,bb[3]))
            dup = False
            for sb in seen_boxes:
                ix0, iy0 = max(new_box[0], sb[0]), max(new_box[1], sb[1])
                ix1, iy1 = min(new_box[2], sb[2]), min(new_box[3], sb[3])
                if ix1 > ix0 and iy1 > iy0:
                    inter = (ix1-ix0)*(iy1-iy0)
                    a1 = (new_box[2]-new_box[0])*(new_box[3]-new_box[1])
                    a2 = (sb[2]-sb[0])*(sb[3]-sb[1])
                    if inter / min(a1, a2 or 1) > 0.5:
                        dup = True; break
            if dup:
                continue

            # Trusted Face Whitelist check
            is_trusted = False
            if ref_embeddings and face.normed_embedding is not None:
                max_sim = 0
                for ref_embedding in ref_embeddings:
                    sim = np.dot(ref_embedding, face.normed_embedding)
                    max_sim = max(max_sim, sim)
                    if sim > 0.25:  # Threshold for buffalo_l / arcface (Lowered for better matching)
                        print(f"[InsightFace] Skipping trusted face (sim: {sim:.2f})")
                        is_trusted = True
                        break
                if not is_trusted:
                    print(f"[InsightFace] Face not trusted (max_sim: {max_sim:.2f})")
                    
            if is_trusted:
                continue

            seen_boxes.append(new_box)
            dets.append(make_det(
                "face", "Face", "[FACE]", conf,
                new_box[0], new_box[1], new_box[2], new_box[3], W, H,
                uid=f"iface-{i}"
            ))
        print(f"[InsightFace] {len(dets)} face(s) redacted, out of {valid_faces_count} valid face(s) found.")
        return dets, valid_faces_count
    except Exception as e:
        print(f"[InsightFace] Runtime error: {e}")
        return [], 0

# =============================================================================
# LAYER 7 — MEDIAPIPE (dual-model, close + far)
# =============================================================================

def run_mediapipe_faces(img, W, H) -> List[Detection]:
    """MediaPipe face detection with low confidence threshold + upscale pass for small faces."""
    dets = []
    try:
        import mediapipe as mp
        mp_fd = mp.solutions.face_detection

        def process_frame(frame, scale=1.0, model_sel=0, prefix="mp"):
            # High threshold (0.65) prevents false positives on card stripes/numbers
            with mp_fd.FaceDetection(model_selection=model_sel, min_detection_confidence=0.65) as fd:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = fd.process(rgb)
                results = []
                if res.detections:
                    for i, det in enumerate(res.detections):
                        bb = det.location_data.relative_bounding_box
                        x0 = max(0.0, (bb.xmin / scale) * 100)
                        y0 = max(0.0, (bb.ymin / scale) * 100)
                        x1 = min(100.0, ((bb.xmin + bb.width) / scale) * 100)
                        y1 = min(100.0, ((bb.ymin + bb.height) / scale) * 100)
                        conf = float(det.score[0] * 100)
                        # Extra aspect-ratio guard at collection time
                        w_pct = x1 - x0; h_pct = y1 - y0
                        if h_pct > 0 and 0.35 <= (w_pct / h_pct) <= 2.5:
                            results.append(Detection(
                                id=f"{prefix}-m{model_sel}-{i}",
                                type="face", label="Face", text="[FACE]",
                                confidence=conf,
                                bbox=BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1),
                                redacted=True,
                            ))
                return results

        # Only normal-size passes — the 2x upscale pass caused false positives on
        # card decoration elements (stripes, numbers, logos)
        # Using model_sel=1 for full range to avoid running twice
        dets.extend(process_frame(img, scale=1.0, model_sel=1, prefix="mp1"))

    except Exception as e:
        print(f"[MediaPipe] Error: {e}")
    return dets

# =============================================================================
# LAYER 8 — OPENCV HAAR + DNN FALLBACK
# =============================================================================

def run_opencv_faces(img, W, H) -> List[Detection]:
    """Haar cascade fallback with smaller minSize and upscale pass for tiny faces."""
    dets = []
    try:
        gray    = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        cascade = get_haar_cascade()

        # Haar Cascade (frontal) — stricter minNeighbors to eliminate card noise
        # Only single pass at native resolution (no 2x — causes false positives on IDs)
        faces_haar = cascade.detectMultiScale(
            gray, scaleFactor=1.05, minNeighbors=7,
            minSize=(40, 40), flags=cv2.CASCADE_SCALE_IMAGE
        )
        for i, (x, y, fw, fh) in enumerate(faces_haar if len(faces_haar) else []):
            # Aspect ratio sanity: a face is roughly square
            if 0.5 <= fw / max(fh, 1) <= 1.8:
                dets.append(make_det(
                    "face", "Face", "[FACE]", 75.0,
                    x, y, x + fw, y + fh, W, H, uid=f"haar-{i}"
                ))

        # Profile face cascade with same strict settings
        cascade_profile = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_profileface.xml"
        )
        faces_profile = cascade_profile.detectMultiScale(
            gray, scaleFactor=1.05, minNeighbors=7,
            minSize=(40, 40), flags=cv2.CASCADE_SCALE_IMAGE
        )
        for i, (x, y, fw, fh) in enumerate(faces_profile if len(faces_profile) else []):
            if 0.4 <= fw / max(fh, 1) <= 2.0:
                dets.append(make_det(
                    "face", "Face", "[FACE]", 72.0,
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
            "ner":         "GLiNER / knowledgator/gliner-pii-base-v1.0 (lazy)",
            "face":        "InsightFace SCRFD + MediaPipe + Haar Cascade",
            "qr":          "pyzbar + OpenCV",
            "regex":       "V4 — Aadhaar/VID/masked, PAN, Mobile+91, DOB×8, OTP, UPI, GSTIN, Card",
        }
    }


from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        # Remove input to prevent UnicodeDecodeError on raw bytes
        if "input" in error:
            del error["input"]
        errors.append(error)
    return JSONResponse(
        status_code=422,
        content={"detail": errors},
    )

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
            
        # 1. Extreme speedup: limit dimensions to 640 for processing
        h, w = img.shape[:2]
        max_dim = 480  # Reduced from 640 → 25% speedup (area -44%)
        if w > max_dim or h > max_dim:
            scale = max_dim / max(w, h)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h))
            
        H, W = img.shape[:2]
    except Exception as e:
        raise HTTPException(400, f"Image decode: {e}")

    # ── Run heavy models sequentially to prevent CPU thread thrashing ────────
    def do_ocr():
        t_s = time.time()
        ocr = get_ocr_model()
        r = ocr.predict(img) if hasattr(ocr, "predict") else ocr.ocr(img)
        print(f"[Profile] OCR took {(time.time() - t_s)*1000:.1f}ms")
        return r
        
    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_ocr     = executor.submit(do_ocr)
            future_iface   = executor.submit(run_insightface, img, W, H, req.trusted_faces_base64)
            future_mp      = executor.submit(run_mediapipe_faces, img, W, H)
            future_yolo    = executor.submit(run_yolo_safety, img, W, H)
            future_nudenet = executor.submit(run_nudenet, img, W, H)
            future_weapons = executor.submit(run_weapons_detector, img, W, H)
            future_smoking = executor.submit(run_smoking_detector, img, W, H)
            future_plates  = executor.submit(run_plate_detector, img, W, H)

            result    = future_ocr.result()
            iface_d, iface_total = future_iface.result()
            mp_d      = future_mp.result()
            yolo_d    = future_yolo.result()
            nudenet_d = future_nudenet.result()
            weapons_d = future_weapons.result()
            smoking_d = future_smoking.result()
            plates_d  = future_plates.result()
            
        lines  = parse_ocr(result, img)
        qr_d    = run_qr(img, W, H)
        haar_d  = []
    except Exception as e:
        raise HTTPException(500, f"Engine execution: {e}")

    # ── Process OCR outputs ───────────────────────────────────────────────────
    full_text = " ".join(str(ln[1][0]) for ln in lines if ln[1][0])
    words_out = []
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

    # ── Text Analytics ────────────────────────────────────────────────────────
    full_text_upper = full_text.upper()
    doc_type = "unknown"
    if "GOVERNMENT OF INDIA" in full_text_upper or "UNIQUE IDENTIFICATION" in full_text_upper or "AADHAAR" in full_text_upper:
        doc_type = "aadhaar"
    elif "INCOME TAX DEPARTMENT" in full_text_upper or "PAN" in full_text_upper:
        doc_type = "pan"

    regex_d = run_regex(lines, W, H)
    multi_d = run_multi_box_regex(lines, W, H)
    addr_d  = run_address_rules(lines, W, H)
    
    if not full_text.strip():
        ner_d = []
        llm_d = []
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_ner = executor.submit(run_gliner, lines, W, H)
            future_llm = executor.submit(run_llm_extractor, full_text, lines, W, H)
            ner_d = future_ner.result()
            llm_d = future_llm.result()
    
    # ── InsightFace-first strategy ────────────────────────────────────────────
    # InsightFace (SCRFD) is the most accurate deep-learning detector.
    # Haar + MediaPipe are noisy on structured images (ID cards, forms).
    # Only include them when InsightFace found ZERO faces.
    if iface_total > 0:
        # InsightFace found faces (even if they were all skipped because they are trusted).
        # We skip Haar and MediaPipe so we don't re-detect the trusted faces.
        face_sources = iface_d
        print(f"[FaceStrategy] InsightFace found {iface_total} face(s). Ignoring Haar/MediaPipe.")
    else:
        # InsightFace found nothing → allow Haar/MediaPipe as fallback
        face_sources = mp_d + haar_d
        print(f"[FaceStrategy] InsightFace=0, falling back to MP({len(mp_d)})+Haar({len(haar_d)})")

    # Safety detections from dedicated models (always redacted, bypassed by NMS)
    safety_d = nudenet_d + weapons_d + smoking_d + plates_d + yolo_d
    all_dets = regex_d + multi_d + ner_d + addr_d + llm_d + face_sources + qr_d + safety_d
    if safety_d:
        print(f"[YOLO] Added {len(yolo_d)} safety detection(s): {[d.label for d in yolo_d]}")

    # ── Global semantic deduplication (before NMS) ────────────────────────────
    # When multiple engines detect the same value (e.g. Aadhaar from both run_regex
    # and run_multi_box_regex), keep only the highest-confidence detection.
    # Key = (type, normalized_text). This eliminates cross-engine duplicates.
    def _norm_text(t: str) -> str:
        return re.sub(r'[\s\-]', '', t.lower().strip())[:40]

    type_text_seen: dict = {}
    for d in sorted(all_dets, key=lambda x: x.confidence, reverse=True):
        if d.type == "face":
            # Don't semantically deduplicate faces by text, since all faces have text "[FACE]"
            # Include bbox coordinates in key to avoid dropping secondary faces
            key = f"face:{d.bbox.x0}:{d.bbox.y0}:{d.bbox.x1}:{d.bbox.y1}"
        else:
            key = f"{d.type}:{_norm_text(d.text)}"
            
        if key not in type_text_seen:
            type_text_seen[key] = d
    all_dets = list(type_text_seen.values())

    # ── Per-type NMS with industry-tuned IoU thresholds ───────────────────────
    # Faces: 0.35 (keep distinct face thumbnails that may be close together)
    # IDs/structured (Aadhaar, PAN, DOB): 0.20 (very aggressive — same number = same box)
    # Names/addresses: 0.25 (slightly more generous for multi-word spans)
    # Other text: 0.30
    HIGH_OVERLAP_TYPES = {"aadhaar", "pan", "dob", "credit_card", "bank_account",
                          "phone", "email", "passport", "voter_id", "gstin", "upi",
                          "license_plate", "otp", "qr"}
    NAME_TYPES = {"name", "address", "pincode"}

    face_dets  = [d for d in all_dets if d.type == "face"]
    high_dets  = [d for d in all_dets if d.type in HIGH_OVERLAP_TYPES]
    name_dets  = [d for d in all_dets if d.type in NAME_TYPES]
    other_dets = [d for d in all_dets if d.type not in HIGH_OVERLAP_TYPES
                  and d.type not in NAME_TYPES and d.type != "face"]

    merged_faces = nms(face_dets, thr=0.35)
    merged_high  = nms(high_dets,  thr=0.20)   # very tight — same ID should merge
    merged_names = nms(name_dets,  thr=0.25)
    merged_other = nms(other_dets, thr=0.30)

    merged = merged_faces + merged_high + merged_names + merged_other
    merged = [d for d in merged if (d.bbox.x1 - d.bbox.x0) > 0 and (d.bbox.y1 - d.bbox.y0) > 0]

    # ── Confidence floor: discard below suggestion threshold ─────────────────
    before_floor = len(merged)
    merged = [d for d in merged if d.type == "face" or d.confidence >= _SUGGEST_THRESHOLD]
    if before_floor != len(merged):
        print(f"[ConfidenceFloor] Dropped {before_floor - len(merged)} low-confidence detections (<{_SUGGEST_THRESHOLD}%)")

    # ── Multi-layer face sanity filter ───────────────────────────────────────
    def is_valid_face(d):
        if d.type != "face":
            return True
        w_pct = d.bbox.x1 - d.bbox.x0   # 0–100 %
        h_pct = d.bbox.y1 - d.bbox.y0
        
        # Removed Aadhaar ROI filtering to allow ghost faces on the right side
                
        # 1) Size: must be 1%–45% of image in each dimension
        if not (1.0 <= w_pct <= 45.0 and 1.0 <= h_pct <= 45.0):
            return False
        # 2) Aspect ratio: faces are roughly square (allow 0.35–2.5)
        aspect = w_pct / max(h_pct, 0.01)
        if not (0.35 <= aspect <= 2.5):
            return False
        # 3) Confidence floor: reject weak detections that are likely false positives
        if d.confidence < 20.0:
            return False
        
        # 4) OCR Density / Overlap Suppression: Logos/icons often trigger false faces but contain text.
        face_area = (d.bbox.x1 - d.bbox.x0) * (d.bbox.y1 - d.bbox.y0)
        ocr_words_in_face = 0
        for ln in lines:
            box, (t, _) = ln
            word_count = len(str(t).strip().split())
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            lx0, ly0 = max(0.0, min(100.0, min(xs) / W * 100)), max(0.0, min(100.0, min(ys) / H * 100))
            lx1, ly1 = max(0.0, min(100.0, max(xs) / W * 100)), max(0.0, min(100.0, max(ys) / H * 100))
            
            ix0, iy0 = max(d.bbox.x0, lx0), max(d.bbox.y0, ly0)
            ix1, iy1 = min(d.bbox.x1, lx1), min(d.bbox.y1, ly1)
            
            if ix1 > ix0 and iy1 > iy0:
                inter = (ix1 - ix0) * (iy1 - iy0)
                # Count if text box is substantially inside face
                if inter / ((lx1 - lx0) * (ly1 - ly0) + 1e-5) > 0.40:
                    ocr_words_in_face += word_count
                
                # Check 8+ OCR words overlap for suppression
                if ocr_words_in_face >= 8:
                    return False
        return True


    before_filter = len([d for d in merged if d.type == "face"])    
    merged = [d for d in merged if is_valid_face(d)]
    
    # Extract AI description from special detection
    ai_desc = ""
    for d in merged:
        if d.type == "ai_desc":
            ai_desc = d.text
    
    # Remove ai_desc from the final list
    merged = [d for d in merged if d.type != "ai_desc"]

    t1 = time.time()
    after_filter = len([d for d in merged if d.type == "face"])
    if before_filter != after_filter:
        print(f"[FaceFilter] Removed {before_filter - after_filter} invalid face bbox(es)")

    # Calculate dynamic privacyScore
    base_score = 100
    for d in merged:
        if d.type in ["face", "aadhaar", "pan"]:
            base_score -= 20
        elif d.type in ["phone", "email"]:
            base_score -= 15
        else:
            base_score -= 5
    privacy_score = max(0, min(100, base_score))

    ms = int((time.time() - t0) * 1000)
    print(
        f"[Scan] {ms}ms | W={W} H={H} | "
        f"lines={len(lines)} regex={len(regex_d)} ner={len(ner_d)} "
        f"addr={len(addr_d)} iface={len(iface_d)} mp={len(mp_d)} "
        f"qr={len(qr_d)} -> merged={len(merged)} | Privacy={privacy_score}"
    )

    return ScanResponse(
        detections=merged,
        words=words_out,
        fullText=full_text.strip(),
        processingTime=ms,
        aiDescription=ai_desc,
        privacyScore=privacy_score
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)

