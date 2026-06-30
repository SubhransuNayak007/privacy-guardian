import re

with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update GLiNER model
content = content.replace('"urchade/gliner_base"', '"knowledgator/gliner-pii-base-v1.0"')
content = content.replace('urchade/gliner_base', 'knowledgator/gliner-pii-base-v1.0')

# 2. Add Verhoeff Checksum Validator and validate_face_landmarks
verhoeff_code = """# =============================================================================
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
"""
content = content.replace('# =============================================================================\n# HELPER FUNCTIONS\n# =============================================================================', verhoeff_code)

# 3. Add Document Type Detection
doc_type_code = """    # ── Text Analytics ────────────────────────────────────────────────────────
    full_text_upper = full_text.upper()
    doc_type = "unknown"
    if "GOVERNMENT OF INDIA" in full_text_upper or "UNIQUE IDENTIFICATION" in full_text_upper or "AADHAAR" in full_text_upper:
        doc_type = "aadhaar"
    elif "INCOME TAX DEPARTMENT" in full_text_upper or "PAN" in full_text_upper:
        doc_type = "pan"
"""
content = content.replace('    # ── Text Analytics ────────────────────────────────────────────────────────', doc_type_code)

# 4. Filter Aadhaar via Verhoeff
# In run_regex
run_regex_mod = """        # Run each pattern
        for type_str, label, pat, base_conf in REGEX_TABLE:
            for m in pat.finditer(text_s):
                mt = m.group(0).strip()
                # Apply Verhoeff for plain 12-digit Aadhaar
                if type_str == "aadhaar" and label == "Aadhaar Number":
                    if not is_valid_aadhaar_verhoeff(mt):
                        continue
                key = f"{type_str}:{mt}"
"""
content = content.replace("""        # Run each pattern
        for type_str, label, pat, base_conf in REGEX_TABLE:
            for m in pat.finditer(text_s):
                mt = m.group(0).strip()
                key = f"{type_str}:{mt}"
""", run_regex_mod)

# In run_multi_box_regex
multi_box_mod = """    for type_str, label, pat, conf in patterns:
        for m in pat.finditer(text):
            mt = m.group(0).strip()
            if type_str == "aadhaar" and label == "Aadhaar Number":
                if not is_valid_aadhaar_verhoeff(mt):
                    continue
"""
content = content.replace("""    for type_str, label, pat, conf in patterns:
        for m in pat.finditer(text):
            mt = m.group(0).strip()
""", multi_box_mod)

# 5. Integrate face landmark validation inside run_insightface
insightface_mod = """            if getattr(face, "kps", None) is None or len(face.kps) < 5:
                continue
            if not validate_face_landmarks(face.kps):
                continue
"""
content = content.replace("""            if getattr(face, "kps", None) is None or len(face.kps) < 5:
                continue
""", insightface_mod)

# 6. Add ROI check and OCR density check inside is_valid_face
is_valid_face_mod = """    # ── Multi-layer face sanity filter ───────────────────────────────────────
    def is_valid_face(d):
        if d.type != "face":
            return True
        w_pct = d.bbox.x1 - d.bbox.x0   # 0–100 %
        h_pct = d.bbox.y1 - d.bbox.y0
        
        # Aadhaar ROI filtering: Face MUST be on the left side (x0 < 45%)
        if doc_type == "aadhaar":
            if d.bbox.x0 > 45.0:  # Allow up to 45% to be safe
                return False
                
        # 1) Size: must be 1%–45% of image in each dimension
        if not (1.0 <= w_pct <= 45.0 and 1.0 <= h_pct <= 45.0):
            return False
        # 2) Aspect ratio: faces are roughly square (allow 0.35–2.5)
        aspect = w_pct / max(h_pct, 0.01)
        if not (0.35 <= aspect <= 2.5):
            return False
        # 3) Confidence floor: reject weak detections that are likely false positives
        if d.confidence < 60.0:
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
"""

content = content.replace("""    # ── Multi-layer face sanity filter ───────────────────────────────────────
    def is_valid_face(d):
        if d.type != "face":
            return True
        w_pct = d.bbox.x1 - d.bbox.x0   # 0–100 %
        h_pct = d.bbox.y1 - d.bbox.y0
        # 1) Size: must be 1%–45% of image in each dimension
        if not (1.0 <= w_pct <= 45.0 and 1.0 <= h_pct <= 45.0):
            return False
        # 2) Aspect ratio: faces are roughly square (allow 0.35–2.5)
        aspect = w_pct / max(h_pct, 0.01)
        if not (0.35 <= aspect <= 2.5):
            return False
        # 3) Confidence floor: reject weak detections that are likely false positives
        if d.confidence < 60.0:
            return False
        
        # 4) OCR Overlap Suppression: Logos/icons often trigger false faces but contain text.
        face_area = w_pct * h_pct
        for ln in lines:
            box, (t, _) = ln
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            lx0, ly0 = max(0.0, min(100.0, min(xs) / W * 100)), max(0.0, min(100.0, min(ys) / H * 100))
            lx1, ly1 = max(0.0, min(100.0, max(xs) / W * 100)), max(0.0, min(100.0, max(ys) / H * 100))
            
            ix0, iy0 = max(d.bbox.x0, lx0), max(d.bbox.y0, ly0)
            ix1, iy1 = min(d.bbox.x1, lx1), min(d.bbox.y1, ly1)
            
            if ix1 > ix0 and iy1 > iy0:
                inter = (ix1 - ix0) * (iy1 - iy0)
                # If text overlaps more than 15% of the face, or face covers 50% of text
                if inter / face_area > 0.15 or inter / ((lx1 - lx0) * (ly1 - ly0) + 1e-5) > 0.50:
                    return False
        return True""", is_valid_face_mod)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Engine patched successfully!")
