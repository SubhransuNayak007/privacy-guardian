import re

def is_indian_name(text: str) -> bool:
    text = text.strip()
    words = text.split()
    if len(words) < 2 or len(words) > 3:
        return False
        
    for w in words:
        # Check if word is alphabetic and capitalized (e.g. Name or NAME)
        if not w.isalpha():
            return False
        if not (w.isupper() or (w[0].isupper() and (len(w) == 1 or w[1:].islower()))):
            return False
            
    # Common words on government ID cards to exclude
    blacklist = {
        "government", "india", "aadhaar", "unique", "identification", "authority", 
        "male", "female", "dob", "date", "birth", "year", "issue", "address", 
        "father", "mother", "spouse", "card", "number", "of", "identity", 
        "citizenship", "verification", "online", "authentication", "xml", "offline",
        "signature", "holder", "thumb", "impression", "enrolment", "state", "district",
        "post", "office", "no", "id", "card", "tax", "income", "department", "goi"
    }
    
    for w in words:
        if w.lower() in blacklist:
            return False
            
    return True

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
        
    # Name check
    if is_indian_name(text):
        return "name"
        
    # OTP / PIN / Passwords
    if re.search(r'\b(OTP|One Time Password|Verification Code|Secure Code|Pin Code|PIN|One-Time)\b', text, re.IGNORECASE):
        return "password"
    if re.search(r'\b\d{4,6}\b', text):
        return "password"
        
    if re.search(r'\b(Name|Father|Gender|Male|Female)\b', text, re.IGNORECASE):
        return "pii_text"
    return ""
