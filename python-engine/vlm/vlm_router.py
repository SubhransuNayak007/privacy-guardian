def call_vlm(img_crop, doc_type: str, confidence: float):
    # Conditional loading of Florence-2
    # Only triggered if confidence < 0.8 on a complex doc
    if confidence >= 0.8:
        return None
        
    print(f"Triggering Tier-2 VLM for {doc_type} due to low confidence ({confidence})...")
    # MOCK implementation to prevent VRAM overflow on standard servers
    return {"extracted_text": "MOCKED_VLM_TEXT", "sensitive_regions": []}
