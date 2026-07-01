def calculate_risk_score(detections: list) -> str:
    score = 0
    for d in detections:
        lbl = d.get("label", "")
        if lbl in ["credit_card", "passport", "pan", "aadhaar"]:
            score += 100
        elif lbl in ["face"]:
            score += 20
        elif lbl in ["qr", "barcode"]:
            score += 40
        elif lbl in ["phone", "email"]:
            score += 10
            
    if score >= 100:
        return "High"
    elif score >= 50:
        return "Medium"
    else:
        return "Low"
