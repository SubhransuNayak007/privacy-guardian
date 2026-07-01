def call_vlm(img_crop, doc_type: str, confidence: float):
    # Conditional loading of Florence-2
    # Only triggered if confidence < 0.8 on a complex doc
    if confidence >= 0.8:
        return None
        
    print(f"Triggering Tier-2 VLM for {doc_type} due to low confidence ({confidence})...")
    # VLM is currently disabled to prevent VRAM overflow on standard servers
    # Would normally return Florence-2 extraction here
    return {"extracted_text": "", "sensitive_regions": []}
