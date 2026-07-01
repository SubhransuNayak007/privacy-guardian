import re

def detect_regex(text: str) -> str:
    clean_digits = re.sub(r'\D', '', text)
    if len(clean_digits) == 12: 
        return "aadhaar"
        
    if re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text):
        return "aadhaar"
    if re.search(r'\b[A-Z]{5}\d{4}[A-Z]\b', text):
        return "pan"
    if re.search(r'\b\d{2}[/\-]\d{2}[/\-]\d{4}\b', text):
        return "dob"
    if re.search(r'\b\d{4}[/\-]\d{2}[/\-]\d{2}\b', text):
        return "dob"
    if re.search(r'\b(DOB|Date of Birth|Birth|YOB)\b', text, re.IGNORECASE):
        return "dob"
    if re.search(r'\b(Name|Father|Gender|Male|Female)\b', text, re.IGNORECASE):
        return "pii_text"
    return ""
