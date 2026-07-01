_presidio = None
def get_presidio():
    global _presidio
    if _presidio is None:
        try:
            from presidio_analyzer import AnalyzerEngine
            _presidio = AnalyzerEngine()
        except:
            _presidio = "unavailable"
    return _presidio

def analyze_text(text: str) -> str:
    p = get_presidio()
    if p == "unavailable" or not p:
        return ""
    try:
        results = p.analyze(text=text, language='en')
        if results:
            # Get highest scoring entity
            best = max(results, key=lambda x: x.score)
            if best.score > 0.5:
                entity = best.entity_type
                if entity == "PERSON":
                    return "name"
                if entity == "EMAIL_ADDRESS":
                    return "email"
                if entity == "PHONE_NUMBER":
                    return "phone"
                if entity == "LOCATION":
                    return "address"
                return entity.lower()
    except Exception as e:
        print(f"Presidio error: {e}")
    return ""
