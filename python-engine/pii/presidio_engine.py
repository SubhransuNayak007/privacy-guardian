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

def analyze_text(text: str) -> list:
    p = get_presidio()
    if p == "unavailable" or not p:
        return []
    try:
        return p.analyze(text=text, language='en')
    except:
        return []
