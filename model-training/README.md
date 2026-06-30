# Address Detection Model Training Pipeline

This directory contains the necessary scripts to train and fine-tune models for Address Detection, exactly as per the requirements for:
1. **Computer Vision (Image Address Blocks)**
2. **NLP / NER (Text BIO Tagging)**
3. **Address Normalization**

Because training models requires significant GPU resources, these scripts are designed to be run on a dedicated machine (like an AWS instance, Google Colab, or a local PC with an NVIDIA GPU).

## 1. Computer Vision (Image Address & Face Detection)
We use Ultralytics YOLOv8 for both Document Layout Analysis (to extract address blocks) and Face Detection.

**Dataset Setup:**
If you don't already have the datasets locally, you can use the automated downloader script to fetch the gold standard benchmarks (WIDER FACE, CelebA, LFW).
1. Install requirements: `pip install datasets torchvision kaggle`
2. Run: `python download_face_datasets.py`
3. The datasets will be downloaded into `model-training/datasets/face-detection/`.

Alternatively, download your YOLO-formatted dataset from Roboflow or Kaggle and extract it into `model-training/datasets/face-detection/` (for faces) or `model-training/datasets/address-layout/` (for addresses).
   - Images should be in `images/train/`
   - Bounding boxes (`[class_id, x_center, y_center, width, height]`) should be in `labels/train/`.

**Training:**
1. Install requirements: `pip install ultralytics`
2. Open `train_yolo_address.py` (for addresses) or `train_yolo_face.py` (for faces) and uncomment the `train_model(yaml_path)` line at the bottom of the script.
3. Run: `python train_yolo_address.py` or `python train_yolo_face.py`
4. The trained model weights will be saved as `best.pt`. You can copy this into the backend to replace the existing logic.

## 2. Address Detection in Text (NLP / NER)
We fine-tune a BERT-based Token Classification model using BIO tags (`B-STREET`, `I-STREET`, etc.).

**Dataset Setup (Kaggle):**
1. Download the Kaggle Delivery Address Dataset.
2. Format it as a JSON file and place it at `model-training/datasets/address-ner/train_bio.json`.
3. The format should be:
   ```json
   [
       {
           "tokens": ["123", "Main", "St", "New", "York"], 
           "ner_tags": ["B-STREET", "I-STREET", "I-STREET", "B-CITY", "I-CITY"]
       }
   ]
   ```

**Training:**
1. Install requirements: `pip install torch transformers datasets`
2. Open `train_ner_address.py` and uncomment `trainer.train()` at the bottom.
3. Run: `python train_ner_address.py`
4. The fine-tuned weights will be saved in `address_ner_model/`.

## 3. Address Matching & Normalization
If you need to resolve messy user input addresses against an authoritative database (like the ResearchGate Semantic Address Matching Dataset).

**Execution:**
1. Open `address_normalization.py` and populate the `AUTHORITATIVE_DB` with your source of truth database.
2. Run: `python address_normalization.py`
3. The script will use Jaccard Similarity and Levenshtein distance to find the closest match.

## 4. Synthetic PII Data Generation (NLP Strategy)
For training NLP models on Indian Identity formats (Aadhaar, Mobile, DOB), you can generate thousands of safe, synthetic training samples.

**Execution:**
1. Install requirement: `pip install faker`
2. Run: `python generate_synthetic_pii.py`
3. The script generates realistic Indian sentences with corresponding PII blocks in `model-training/datasets/address-ner/synthetic_pii.csv`.

## 5. KYC Document Region Detection (Computer Vision OCR Strategy)
For Identity Documents (like KYC uploads), extracting fields precisely requires a multi-stage approach (Detect Region -> Crop -> OCR).

**Dataset Setup (Roboflow Aadhaar Card Dataset):**
1. Download the pre-annotated dataset mapped with `aadhaar_number`, `photo`, `dob` blocks.
2. Extract to `model-training/datasets/kyc-aadhaar/`.

**Training:**
1. Run: `python train_yolo_aadhaar.py`
2. Once the weights are generated, you can run OCR specifically on these cropped regions instead of the entire messy document.
