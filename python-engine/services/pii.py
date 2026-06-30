from models.manager import ModelManager
import re

class PIIService:
    def __init__(self, model_manager: ModelManager):
        self.presidio = model_manager.get_presidio()

    def analyze(self, text: str):
        if re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', text):
            return True
        if re.search(r'\b[A-Z]{5}\d{4}[A-Z]\b', text):
            return True
            
        if self.presidio != "unavailable" and self.presidio:
            try:
                res = self.presidio.analyze(text=text, language='en')
                if res: return True
            except:
                pass
        return False
