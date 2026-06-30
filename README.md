<div align="center">
  <img src="https://via.placeholder.com/150/000000/FFFFFF/?text=PrivacyGuardian" alt="Privacy Guardian Logo" width="150"/>
  
  # Privacy Guardian 🛡️
  
  **Next-Gen AI Privacy Redaction Engine**
  
  [![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
  [![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org/)
  [![YOLOv8](https://img.shields.io/badge/YOLO-v8-yellow)](https://ultralytics.com/)
  [![PaddleOCR](https://img.shields.io/badge/OCR-PaddleOCR-blue)](#)
</div>

<br/>

Privacy Guardian is a blazing-fast, dual-stack application that automatically detects and redacts Personally Identifiable Information (PII), NSFW content, faces, and sensitive identifiers from images.

---

## 🚀 Tech Stack

### Frontend (User Interface)
* **Framework:** Next.js 15 (App Router)
* **Language:** TypeScript
* **Styling:** Tailwind CSS + Custom CSS Variables for seamless Dark/Light theming
* **Animations:** Framer Motion + View Transitions API (120FPS smooth transitions)
* **State Management:** Zustand
* **Storage:** IndexedDB (`idb`) for offline-capable sessions

### Backend (AI Pipeline)
* **Framework:** FastAPI (Python)
* **Multi-Threading:** `ThreadPoolExecutor` with 4-way Tiled Image Processing for 4x speedups!
* **AI Models:**
  * **OCR:** PaddleOCR (Primary) + EasyOCR (Fallback)
  * **Face Detection:** InsightFace, MediaPipe v2, Haar Cascades
  * **Object Detection:** YOLOv8n (Weapons, People)
  * **NSFW Filter:** NudeNet (Exposed body parts)
  * **License Plates:** fast-alpr (ONNX)
* **Heuristics:** Regex for Indian PII (Aadhaar, PAN, GSTIN), Shipping Label Rules, Signature Detection

---

## 🧠 Problems & Solutions

### 1. High Latency on Large Images
**Problem:** Processing a single high-res image through 6 heavy AI models sequentially took up to 300 seconds, causing API timeouts.
**Solution:** Implemented **4-Way Concurrent Tiling**. The image is split into 4 quadrants, and each quadrant is processed in parallel using `concurrent.futures`. Detections are mapped back to global coordinates. **Result: ~4x faster detection.**

### 2. Vercel Serverless Function Timeouts
**Problem:** Free tier Vercel times out at 10 seconds, which wasn't enough even for local proxying.
**Solution:** Configured `maxDuration = 60` in Next.js API routes and optimized the backend pipeline to fit within standard serverless limits.

### 3. False Positives on Non-Faces
**Problem:** Basic Haar cascades flagged random circular textures and text as faces.
**Solution:** Upgraded to **InsightFace** and **MediaPipe v2 Tasks API** for robust facial recognition, retaining Haar only as a strict fallback.

### 4. Bounding Box Rendering Bugs
**Problem:** Blur wasn't applying because detection bounding boxes were returning `0` width/height.
**Solution:** Fixed relative percentage scaling `(bbox.x1 - bbox.x0) / 100 * width_px` in the Canvas engine, ensuring perfect 1:1 redactions.

### 5. UI/UX Clashing on Mobile Devices
**Problem:** The Developer Tools panel overlapped with the primary Results Screen action buttons on mobile screens.
**Solution:** Handled Z-index and responsive layout adjustments (`hidden md:flex flex-col` or `bottom-24` anchors) to keep the UI clean across viewports.

---

## 🛠️ Where to Deploy?

* **Frontend:** Deploy seamlessly on **Vercel** or **Netlify**.
* **Backend:** Deploy on **AWS (EC2 / EKS)**, **Render**, or **Google Cloud Run**. Because of Heavy ML dependencies (OpenCV, PaddlePaddle, PyTorch), deploying via Docker with at least 4GB RAM is highly recommended over serverless platforms (like AWS Lambda).

---

<div align="center">
  <i>Built with ❤️ for Privacy and Security.</i>
</div>
