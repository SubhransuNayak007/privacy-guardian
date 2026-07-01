import re

def is_indian_name(text: str) -> bool:
    text = text.strip()
    words = text.split()
    if len(words) < 2 or len(words) > 4:
        return False
        
    for w in words:
        # Check if word is alphabetic
        if not w.isalpha():
            return False
            
        # Only enforce title/upper casing for English (ASCII) words
        # Hindi/regional scripts don't have casing, so w.isascii() protects them
        if w.isascii():
            if not (w.isupper() or (w[0].isupper() and (len(w) == 1 or w[1:].islower()))):
                return False
            
    # Common words on government ID cards to exclude
    blacklist = {
        "government", "india", "aadhaar", "unique", "identification", "authority", 
        "male", "female", "dob", "date", "birth", "year", "issue", "address", 
        "father", "mother", "spouse", "card", "number", "of", "identity", 
        "citizenship", "verification", "online", "authentication", "xml", "offline",
        "signature", "holder", "thumb", "impression", "enrolment", "state", "district",
        "post", "office", "no", "id", "tax", "income", "department", "goi",
        "mera", "pehchan", "meripehchan", "yojna", "sarkar"
    }
    
    for w in words:
        if w.lower() in blacklist:
            return False
            
    return True

def detect_regex(text: str) -> str:
    # 1. Aadhaar
    clean_digits = re.sub(r'\D', '', text)
    if len(clean_digits) == 12: 
        return "aadhaar"
    if re.search(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b', text):
        return "aadhaar"
        
    # 2. PAN
    if re.search(r'\b[A-Z]{5}\d{4}[A-Z]\b', text):
        return "pan"
        
    # 3. DOB
    if re.search(r'\b\d{2}[/\-]\d{2}[/\-]\d{4}\b', text):
        return "dob"
    if re.search(r'\b\d{4}[/\-]\d{2}[/\-]\d{2}\b', text):
        return "dob"
    if re.search(r'\b(DOB|Date of Birth|Birth|YOB)\b', text, re.IGNORECASE):
        return "dob"
        
    # 4. Address (Expanded to include typical Indian address components and pincodes)
    if re.search(r'\b(Address|C/O|S/O|D/O|W/O|Sector|Phase|Gali|Marg|Bhavan|Nagar|Vihar|Khand|DIST)\b', text, re.IGNORECASE):
        return "address"
    if re.search(r'\b\d{6}\b', text): # Indian Pincode
        return "address"
        
    # 5. Name check
    if is_indian_name(text):
        return "name"
        
    # 6. OTP / Passwords (Strict matching to prevent overriding other fields)
    if re.search(r'\b(OTP|One Time Password|Verification Code|Secure Code|Pin Code|PIN)\b', text, re.IGNORECASE):
        return "password"
        
    # 7. Credit / Debit Cards
    if re.search(r'\b(?:\d[ -]*?){13,16}\b', text):
        return "credit_card"
        
    # 8. Emails
    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', text):
        return "email"
        
    # 9. Phone Numbers (India / International fallback)
    if re.search(r'\b(?:\+?91[\-\s]?)?[6789]\d{9}\b', text) or re.search(r'\b\d{3}[\-\.\s]??\d{3}[\-\.\s]??\d{4}\b', text):
        return "phone"
        
    # 10. Passport & Voter ID
    if re.search(r'\b[A-PR-WYa-pr-wy][1-9]\d\s?\d{4}[1-9]\b', text, re.IGNORECASE): # Indian Passport
        return "passport"
    if re.search(r'\b[A-Z]{3}\d{7}\b', text, re.IGNORECASE): # EPIC / Voter ID
        return "voter_id"
        
    # 11. Social Media Handles
    if re.search(r'(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+[A-Za-z0-9_]+)', text):
        return "social_media"
        
    # 12. Generic PII headers
    if re.search(r'\b(Name|Father|Gender|Male|Female)\b', text, re.IGNORECASE):
        return "pii_text"
        
    return ""
