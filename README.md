<div align="center">
  <h1>🛡️ Privacy Guardian</h1>
  <p><strong>Intelligent AI-Powered Image Redaction & Privacy Engine</strong></p>
</div>

<br />

Privacy Guardian is a full-stack, AI-driven application designed to automatically scan, detect, and redact sensitive information from images before they are shared. Built with a high-performance **11-Layer Machine Learning Pipeline**, it identifies PII (Personally Identifiable Information), NSFW content, faces, signatures, license plates, and sensitive documents with extreme accuracy.

## ✨ Features

- **11-Layer AI Pipeline:** Utilizes 6 concurrent machine learning models + 5 heuristic text layers.
- **Smart Redaction:** Automatically blurs sensitive regions, preserving the context while destroying the data.
- **Real-time Pipeline:** Highly optimized using Python `ThreadPoolExecutor` for concurrent CPU execution.
- **Premium UI/UX:** Built with Next.js, Framer Motion, and Tailwind CSS. Features an insanely smooth, cinematic dark/light mode toggle.
- **Secure Authentication:** Integrated with Supabase for robust user authentication.
- **Public Tunneling:** Connects a Vercel Edge frontend directly to a local Python AI engine via Localtunnel.

---

## 🛠️ Tech Stack

### Frontend & UI
- **Framework:** Next.js (App Router), React
- **Styling:** Tailwind CSS, `next-themes`
- **Animations:** Framer Motion, View Transitions API
- **Components:** Radix UI, Lucide React

### Backend & AI Engine
- **Server:** FastAPI, Uvicorn, Python
- **Computer Vision:** OpenCV, NumPy
- **Machine Learning Models:**
  - **PaddleOCR & EasyOCR** (Optical Character Recognition)
  - **YOLOv8** (Object detection for weapons, people)
  - **InsightFace & MediaPipe** (Face detection)
  - **fast-alpr / MobileViT** (License plate detection)
  - **NudeNet** (NSFW content detection)
  - **PyZBar** (QR/Barcode scanning)

### Infrastructure & Deployment
- **Database / Auth:** Supabase
- **Frontend Hosting:** Vercel
- **Backend Tunneling:** Localtunnel (`npx localtunnel`)

---

## 🚀 Problems & Solutions

Building Privacy Guardian presented several unique engineering challenges, particularly around processing speed and detection accuracy:

### 1. The 300-Second Processing Bottleneck
**Problem:** Initially, the system was taking 4-5 minutes (300 seconds) to process a single image. Running 6 heavy ML models (YOLO, PaddleOCR, InsightFace, etc.) sequentially on massive 4K phone camera uploads maxed out the CPU.
**Solution:** 
- **Intelligent Downscaling:** Added logic to downscale images to a maximum dimension of `960px` before feeding them into the models, cutting the pixel count by ~45% with no loss in OCR readability.
- **Concurrent Execution:** Rewrote the core `scan` endpoint using Python's `concurrent.futures.ThreadPoolExecutor`. Instead of waiting for one model to finish, all independent ML models now run simultaneously across the CPU's multi-cores.

### 2. Missing OCR Fallback
**Problem:** PaddleOCR is fast but struggles with rotated or highly obscured text. The pipeline was designed to fall back to `EasyOCR`, but the library was missing, causing silent failures on hard-to-read documents.
**Solution:** Installed the `easyocr` dependencies (`torch`, `torchvision`, etc.) and wired it into a robust `try/except` fallback loop to guarantee text extraction regardless of the document's orientation.

### 3. Theme Toggle Animation Overlaps
**Problem:** The cinematic circle-wipe animation between light and dark modes looked unnatural because the newly generated view was always expanding outward, making transitions back to light mode feel jarring.
**Solution:** Modified the View Transitions logic. When transitioning from Light ➡️ Dark, the Dark theme expands outward. When transitioning from Dark ➡️ Light, the Dark theme shrinks inward into a circle, revealing the Light theme underneath, creating a perfectly polished and reversible interaction.

---

## 💻 Running Locally

### 1. Start the Python AI Engine
```bash
cd python-engine
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Start the Frontend
```bash
npm install
npm run dev
```

### 3. (Optional) Run the Background Launcher (Windows)
Simply double click `start_background.vbs` to silently launch the Python backend and a public Localtunnel bridge in the background without needing an open terminal! Use `stop_background.bat` to kill the processes.
