# QA Subagent Report: Sections 4 & 5

## Task 2: YOLO Detection
- **Card Detections**: []
- *Note*: Generic YOLO11n missed the custom classes (Credit Card, Key, Gun, Passport MRZ).
## Task 3 & 4: RetinaFace & NudeNet
- *Note*: RetinaFace and NudeNet are not implemented in `ModelManager` or `DetectorService` in this V2 codebase. Detected Face/NSFW via YOLO fallback or missing entirely.
## Task 5: PaddleOCR Selective Triggering
- Router `run_ocr` for document: True
- Router `run_ocr` for key: False (Asserting no full-image OCR)
## Task 6: OCR on Synthetic Credit Card
- Extracted text: 
- Levenshtein Distance for Card Number <= 1: False (Dist: 19)
## Task 7 & 8: Regex & NER
- Text sent to PII Engine: Name: Jane Doe DOB: 01/01/1990 MedID: MED987654321 4532 1234 5678 9012
- Presidio/Regex Triggered: True
## Task 9: OCR Confidence Fallback
- Router `run_vlm` for score=0.75: True (Expected: True)
## Suggestions for missing detection classes
- YOLO11n generic weights do not detect IDs, MRZ, keys, or guns reliably. Fine-tuning is required.
- Integrate NudeNet explicitly in `DetectorService` for NSFW regions.
- Integrate RetinaFace for high-precision face detection.