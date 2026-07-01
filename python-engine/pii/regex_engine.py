import re

def detect_regex(text: str) -> bool:
    if re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text): # Aadhaar
        return True
    if re.search(r'\b[A-Z]{5}\d{4}[A-Z]\b', text): # PAN
        return True
    return False
