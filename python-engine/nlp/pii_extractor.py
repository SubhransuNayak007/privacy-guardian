"""
PII (Personally Identifiable Information) extraction using Regex and SpaCy.
"""

import re
import spacy
from typing import List, Dict, Any

class PIIExtractor:
    """
    Extracts PII entities from text using a combination of regex patterns
    (for structured data like Phone, Email, Aadhaar, PAN) and SpaCy NER
    (for unstructured data like Person names, Locations).
    """
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initializes the PIIExtractor with the specified SpaCy model.
        
        Args:
            model_name (str): The SpaCy model to load.
        """
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            # Fallback or error instruction if model isn't downloaded
            raise OSError(f"SpaCy model '{model_name}' not found. Please run: python -m spacy download {model_name}")
            
        # Regex patterns for Indian context and standard PII
        self.patterns = {
            "PHONE": re.compile(r'\b(?:\+?91[\-\s]?)?[6789]\d{9}\b'),
            "EMAIL": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'),
            "AADHAAR": re.compile(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b'),
            "PAN": re.compile(r'\b[A-Z]{5}\d{4}[A-Z]{1}\b')
        }

    def extract(self, text: str) -> List[Dict[str, Any]]:
        """
        Extracts PII from the given text.
        
        Args:
            text (str): The text to analyze.
            
        Returns:
            List[Dict[str, Any]]: A list of extracted entities with their text, label, and confidence.
        """
        results = []
        
        # 1. Regex Extraction (High Confidence)
        for label, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                results.append({
                    "text": match.group(),
                    "label": label,
                    "confidence": 0.95,
                    "start": match.start(),
                    "end": match.end()
                })
                
        # 2. SpaCy NER Extraction (Moderate Confidence)
        doc = self.nlp(text)
        
        # Map SpaCy labels to our standard labels if needed
        label_mapping = {
            "PERSON": "PERSON",
            "ORG": "ORGANIZATION",
            "GPE": "LOCATION",
            "LOC": "LOCATION"
        }
        
        for ent in doc.ents:
            if ent.label_ in label_mapping:
                # Check for overlaps with regex matches
                is_overlap = any(
                    (ent.start_char >= res['start'] and ent.start_char < res['end']) or
                    (ent.end_char > res['start'] and ent.end_char <= res['end'])
                    for res in results
                )
                
                if not is_overlap:
                    results.append({
                        "text": ent.text,
                        "label": label_mapping[ent.label_],
                        "confidence": 0.75, # Moderate confidence for general NER
                        "start": ent.start_char,
                        "end": ent.end_char
                    })
                    
        # Sort results by starting position for consistency
        results.sort(key=lambda x: x['start'])
        
        # Return format requested: text, label, confidence
        return [
            {
                "text": r["text"], 
                "label": r["label"], 
                "confidence": r["confidence"]
            } 
            for r in results
        ]
