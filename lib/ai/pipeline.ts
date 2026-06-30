/**
 * lib/ai/pipeline.ts
 *
 * Parallel detection pipeline — every detector runs independently.
 *
 * Architecture:
 *   Upload → Preprocess → Promise.allSettled([Face, OCR, QR]) → Merge → Redact
 *
 * If OCR fails   → face detection still runs, QR still runs.
 * If Face fails  → OCR still runs, QR still runs.
 * Never cancel the entire scan because one detector fails.
 */

import { v4 as uuid } from 'uuid';
import { ScanResult, ScanFile, Detection, RiskLevel, PipelineStatus } from '@/types';
import { runOCR, findWordBBoxes } from './vision-client';
import { useEditorStore } from '@/lib/editor-store';
import { convertPdfToImage } from './pdf-handler';
import { scanForPII } from './pii-patterns';
import { detectQRCodes } from './qr-detector';
import { detectFacesMultiStage } from './face-detector';
import { preprocessImage } from './image-preprocessing';

// ── Stage definitions (used for UI animation only) ───────────────────────────
// Total = 15 000 ms to match optimised backend processing time
export const SCAN_STAGES = [
  { id: 'upload',     label: 'Preparing image...',                      duration:  700 },
  { id: 'preprocess', label: 'Preprocessing & enhancing...',            duration: 1000 },
  { id: 'face',       label: 'Detecting faces (InsightFace)...',        duration: 1500 },
  { id: 'body',       label: 'Scanning body parts (NudeNet)...',        duration: 1500 },
  { id: 'ocr',        label: 'Reading text with OCR...',                duration: 2500 },
  { id: 'pii',        label: 'Extracting PII & sensitive data...',      duration: 1500 },
  { id: 'weapons',    label: 'Detecting weapons & illegal items...',     duration: 2000 },
  { id: 'plates',     label: 'Scanning license plates...',              duration: 1200 },
  { id: 'qr',         label: 'Scanning QR codes & barcodes...',         duration:  800 },
  { id: 'risk',       label: 'Calculating privacy risk score...',       duration:  800 },
  { id: 'redact',     label: 'Generating safe version...',              duration: 2500 },
];

// ── Bbox converters ───────────────────────────────────────────────────────────

/**
 * Convert pixel bbox (x0,y0 → x1,y1) to percentage (0–100).
 * Use for Vision API / Tesseract outputs that return pixel coords.
 */
function pixelToPercent(
  x0: number, y0: number, x1: number, y1: number,
  imgW: number, imgH: number,
): Detection['bbox'] {
  return {
    x:      Math.round(Math.max(0, (x0 / imgW) * 100) * 100) / 100,
    y:      Math.round(Math.max(0, (y0 / imgH) * 100) * 100) / 100,
    width:  Math.round(Math.max(0, ((x1 - x0) / imgW) * 100) * 100) / 100,
    height: Math.round(Math.max(0, ((y1 - y0) / imgH) * 100) * 100) / 100,
  };
}

/**
 * Convert normalised bbox (0–1) to percentage (0–100).
 * Use for MediaPipe / jsQR outputs that return 0–1 coords.
 */
function normToPercent(
  x: number, y: number, w: number, h: number,
): Detection['bbox'] {
  return {
    x:      Math.round(Math.max(0, x) * 10000) / 100,
    y:      Math.round(Math.max(0, y) * 10000) / 100,
    width:  Math.round(Math.max(0, w) * 10000) / 100,
    height: Math.round(Math.max(0, h) * 10000) / 100,
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function scoreToRiskLevel(score: number): RiskLevel {
  if (score >= 80) return 'low';
  if (score >= 50) return 'medium';
  if (score >= 20) return 'high';
  return 'critical';
}

function generateRecommendations(detections: Detection[], status: PipelineStatus): string[] {
  const types = new Set(detections.map(d => d.type));
  const recs: string[] = [];

  if (types.has('aadhaar'))      recs.push('Redact your Aadhaar number before sharing this document.');
  if (types.has('pan'))          recs.push('Redact your PAN card number to prevent identity theft.');
  if (types.has('face'))         recs.push('Blur your face before sharing on public platforms.');
  if (types.has('bank_account')) recs.push('Remove bank account details to prevent financial fraud.');
  if (types.has('credit_card'))  recs.push('Redact all credit/debit card information immediately.');
  if (types.has('phone'))        recs.push('Mask your phone number to protect against spam and fraud.');
  if (types.has('email'))        recs.push('Redact your email address to prevent phishing attacks.');
  if (types.has('qr_code'))      recs.push('QR codes may contain embedded personal data — redact them.');
  if (types.has('password'))     recs.push('Never share documents containing passwords or credentials.');
  if (types.has('address'))      recs.push('Mask your physical address to protect your location privacy.');
  if (types.has('signature'))    recs.push('Redact signature regions to prevent forgery.');

  if (status.ocr === 'failed') {
    recs.push(
      'Text detection was unavailable. ' +
      'Manually review this document for sensitive text before sharing.'
    );
  }

  if (recs.length === 0) {
    recs.push('No major privacy issues detected. Always double-check before sharing.');
  }
  return recs;
}

async function getImageDimensions(blob: Blob): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => { resolve({ width: img.width, height: img.height }); URL.revokeObjectURL(url); };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('Failed to read image dimensions')); };
    img.src = url;
  });
}

// ── Safe image generator ──────────────────────────────────────────────────────

export async function generateSafeImage(
  fileBlob: Blob,
  detections: Detection[],
  imgWidth: number,
  imgHeight: number,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(fileBlob);
    const img = new Image();

    img.onload = () => {
      try {
        const canvas = document.createElement('canvas');
        canvas.width  = imgWidth;
        canvas.height = imgHeight;
        const ctx = canvas.getContext('2d');
        if (!ctx) throw new Error('Canvas 2D context not available');

        ctx.drawImage(img, 0, 0, imgWidth, imgHeight);

        for (const det of detections) {
          if (!det.redacted) continue;
          if (det.bbox.width <= 0 || det.bbox.height <= 0) continue;

          const x = (det.bbox.x      / 100) * imgWidth;
          const y = (det.bbox.y      / 100) * imgHeight;
          const w = (det.bbox.width  / 100) * imgWidth;
          const h = (det.bbox.height / 100) * imgHeight;

          // ── REDACTION HELPERS ──────────────────────────────────────────────
          // Apply heavy gaussian blur to a box region (multi-pass for intensity)
          const blurRegion = (
            rx: number, ry: number, rw: number, rh: number,
            blurPx: number, passes: number, ellipse: boolean
          ) => {
            const pad2 = Math.ceil(blurPx * 3);
            const sx = Math.max(0, rx - pad2);
            const sy = Math.max(0, ry - pad2);
            const sw = Math.min(canvas.width  - sx, rw + pad2 * 2);
            const sh = Math.min(canvas.height - sy, rh + pad2 * 2);
            if (sw <= 0 || sh <= 0) return;
            const buf = document.createElement('canvas');
            buf.width = sw; buf.height = sh;
            const bCtx2 = buf.getContext('2d')!;
            bCtx2.filter = `blur(${blurPx}px)`;
            bCtx2.drawImage(canvas, sx, sy, sw, sh, 0, 0, sw, sh);
            for (let p = 1; p < passes; p++) { bCtx2.filter = `blur(${blurPx}px)`; bCtx2.drawImage(buf, 0, 0); }
            bCtx2.filter = 'none';
            ctx.save();
            ctx.beginPath();
            if (ellipse) ctx.ellipse(rx + rw/2, ry + rh/2, rw/2, rh/2, 0, 0, Math.PI*2);
            else ctx.rect(rx, ry, rw, rh);
            ctx.clip();
            ctx.drawImage(buf, sx, sy);
            ctx.restore();
          };
          // Add 5% padding around every detection for full coverage
          const bx = Math.max(0, ((det.bbox.x - 2.5) / 100) * imgWidth);
          const by = Math.max(0, ((det.bbox.y - 2.5) / 100) * imgHeight);
          const bw = Math.min(imgWidth  - bx, ((det.bbox.width  + 5) / 100) * imgWidth);
          const bh = Math.min(imgHeight - by, ((det.bbox.height + 5) / 100) * imgHeight);

          if (det.type === 'face') {
            // FACE: 0.8x radius, 8 passes
            if (det.bbox.width > 55 || det.bbox.height > 55) {
              console.warn(`[Redact] Skipping oversized face bbox: ${det.bbox.width.toFixed(1)}x${det.bbox.height.toFixed(1)}%`);
              continue;
            }
            const blurRadius = Math.max(30, Math.min(bw, bh) * 0.80);
            blurRegion(bx, by, bw, bh, blurRadius, 8, true);

          } else if (det.type === 'nudity' || det.type === 'illegal_item' || det.type === 'license_plate') {
            // SAFETY: 0.8x radius, 8 passes
            const blurRadius = Math.max(40, Math.max(bw, bh) * 0.80);
            blurRegion(bx, by, bw, bh, blurRadius, 8, false);

          } else {
            // TEXT / PII: solid black bar
            const pad = 4;
            ctx.fillStyle = '#000000';
            ctx.beginPath();
            if (typeof (ctx as any).roundRect === 'function') {
              (ctx as any).roundRect(
                Math.max(0, x - pad), Math.max(0, y - pad),
                w + pad * 2, h + pad * 2, 3,
              );
            } else {
              ctx.rect(Math.max(0, x - pad), Math.max(0, y - pad), w + pad * 2, h + pad * 2);
            }
            ctx.fill();
          }
        }

        const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
        URL.revokeObjectURL(url);
        resolve(dataUrl);
      } catch (err) {
        URL.revokeObjectURL(url);
        reject(err);
      }
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to load image for redaction'));
    };
    img.src = url;
  });
}

// ── Pipeline 1: Face Detection ───────────────────────────────────────────────
//
// Browser-side FaceDetector (Chrome AI) is unreliable and not universally
// supported. All face detection is now handled server-side by the V4 Python
// backend (InsightFace SCRFD + MediaPipe + Haar Cascade — triple-layered).
// This pipeline returns an empty array so the Python results are used instead.

async function runFacePipeline(_fileBlob: Blob): Promise<Detection[]> {
  // No-op: Python V4 backend handles all face detection (InsightFace SCRFD +
  // MediaPipe dual-model + Haar frontal + Haar profile).
  return [];
}

// ── Pipeline 2: OCR + PII (Google Cloud Vision / Tesseract server-side) ───────

interface OCRPipelineOutput {
  detections:       Detection[];
  fullText:         string;
  words:            any[];
  labels:           any[];
  visionFaces:      Detection[]; // faces from Vision API (fallback if MediaPipe misses)
  aiDescription?:   string;
  safetyDetections?: any[];      // SafeSearch + Object Localization results
  diagnostics?:     Record<string, string>;
}

async function runOCRPipeline(
  fileBlob: Blob,
  imgW: number,
  imgH: number,
  trustedFaceImages?: string[]
): Promise<OCRPipelineOutput> {
  const ocrResult = await runOCR(fileBlob, trustedFaceImages);

  const piiDetections: Detection[] = [];
  const visionFaces:   Detection[] = [];

  // ── V4: Python backend returns typed detections[] directly ──
  // pythonDetections is the clean array from route.ts (already 0–100% bbox).
  const pythonDetections: Detection[] = (ocrResult as any).pythonDetections || [];
  
  if (pythonDetections.length > 0) {
    // Python V4 returned detections — use them directly, no coord conversion needed.
    for (const det of pythonDetections) {
      piiDetections.push(det);
    }
  } else if (ocrResult.fullText && ocrResult.fullText.trim()) {
    // Fallback for V1 GCV / Tesseract which only returns raw text
    const piiMatches = scanForPII(ocrResult.fullText);

    for (const match of piiMatches) {
      // Use findWordBBoxes to accurately merge OCR word boxes!
      const bboxes = findWordBBoxes(match.rawText, ocrResult.words, imgW, imgH);

      if (bboxes.length > 0) {
        const b = bboxes[0];
        piiDetections.push({
          id:         `pii-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          type:       match.type as any,
          label:      match.label,
          text:       match.maskedText,
          confidence: match.confidence,
          bbox:       normToPercent(b.x, b.y, b.width, b.height),
          redacted:   true,
        });
      } else {
        // PII found in text but no matching word bbox — record without spatial location
        piiDetections.push({
          id:         `pii-txt-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          type:       match.type as any,
          label:      match.label,
          text:       match.maskedText,
          confidence: match.confidence,
          bbox:       { x: 0, y: 0, width: 0, height: 0 },
          redacted:   false, // cannot redact without a location
        });
      }
    }
  }

  // ── Vision API face annotations (fallback — only used when Python backend is down) ──
  for (const [i, face] of ((ocrResult.faces as any[]) || []).entries()) {
    // Skip Vision API faces if Python already detected faces (avoid duplicates)
    if (pythonDetections.some(d => d.type === 'face')) break;
    visionFaces.push({
      id:         `face-vision-${Date.now()}-${i}`,
      type:       'face',
      label:      `Face ${i + 1} (Vision AI)`,
      confidence: Math.round(face.confidence),
      bbox:       pixelToPercent(
        face.bbox.x0, face.bbox.y0,
        face.bbox.x1, face.bbox.y1,
        imgW, imgH,
      ),
      redacted: true,
    });
  }

  // OCR words from V4 are already normalised to 0–100% by the Python backend.
  // Just pass them through as-is.
  
  return { 
    detections: piiDetections, 
    fullText: ocrResult.fullText || '', 
    words: ocrResult.words || [], 
    labels: ocrResult.labels || [],
    visionFaces,
    safetyDetections: (ocrResult as any).safetyDetections || [],
    aiDescription: (ocrResult as any).aiDescription || '',
    diagnostics: ocrResult.diagnostics || {}
  };
}

// ── Pipeline 3: QR Code Detection (jsQR — client-side, offline) ──────────────

async function runQRPipeline(fileBlob: Blob): Promise<Detection[]> {
  const qrs = await detectQRCodes(fileBlob);
  return qrs.map((qr, i) => ({
    id:         `qr-${Date.now()}-${i}`,
    type:       'qr_code' as const,
    label:      'QR Code',
    text:       qr.text.length > 80 ? qr.text.slice(0, 80) + '…' : qr.text,
    confidence: 95,
    // ← normToPercent: jsQR / detectQRCodes returns 0–1 normalised coords
    bbox:       normToPercent(qr.bbox.x, qr.bbox.y, qr.bbox.width, qr.bbox.height),
    redacted:   true,
  }));
}

// ── Main Orchestrator ─────────────────────────────────────────────────────────

export async function runAIPipeline(file: ScanFile): Promise<ScanResult> {
  const t0 = performance.now();

  // ── Step 1: File preparation ──────────────────────────────────────────────
  let fileBlob: Blob;
  if (file.originalFile) {
    fileBlob = file.originalFile;
  } else {
    const resp = await fetch(file.previewUrl);
    if (!resp.ok) throw new Error(`Failed to fetch image (${resp.status})`);
    fileBlob = await resp.blob();
  }

  if (fileBlob.type === 'application/pdf') {
    fileBlob = await convertPdfToImage(fileBlob);
  }
  fileBlob = await preprocessImage(fileBlob);

  const { width: imgW, height: imgH } = await getImageDimensions(fileBlob);

  // ── Step 2: Run ALL detectors concurrently — fully independent ────────────
  //
  //  Promise.allSettled guarantees that ALL three pipelines run to completion
  //  regardless of individual failures. A failed OCR does NOT cancel Face
  //  detection. A failed Face does NOT cancel QR detection.
  //
  const trustedFaceImages = useEditorStore.getState().trustedFaceImages;

  const [faceSettled, ocrSettled, qrSettled] = await Promise.allSettled([
    runFacePipeline(fileBlob),
    runOCRPipeline(fileBlob, imgW, imgH, trustedFaceImages),
    runQRPipeline(fileBlob),
  ]);

  // ── Step 3: Collect results independently ─────────────────────────────────
  const pipelineStatus: PipelineStatus = {
    face:               faceSettled.status === 'fulfilled' ? 'success' : 'failed',
    ocr:                ocrSettled.status  === 'fulfilled' ? 'success' : 'failed',
    qr:                 qrSettled.status   === 'fulfilled' ? 'success' : 'failed',
    documentClassifier: 'skipped',
  };

  const allDetections: Detection[] = [];
  let fullText   = '';
  let ocrWords:  any[]       = [];
  let visionLabels: any[]    = [];
  let visionFaces: Detection[] = [];
  let aiDescription = '';
  let diagnostics: Record<string, string> = {};

  // Face detection result (MediaPipe)
  if (faceSettled.status === 'fulfilled') {
    allDetections.push(...faceSettled.value);
    console.info(`[Pipeline] Face detection ✓ — ${faceSettled.value.length} face(s)`);
  } else {
    console.error('[Pipeline] Face detection ✗:', faceSettled.reason);
  }

  // OCR + PII result
  if (ocrSettled.status === 'fulfilled') {
    allDetections.push(...ocrSettled.value.detections);
    // Safety detections from SafeSearch + Object Localization (already have correct shape)
    if (ocrSettled.value.safetyDetections?.length) {
      allDetections.push(...ocrSettled.value.safetyDetections);
      console.info(`[Pipeline] Safety ✓ → ${ocrSettled.value.safetyDetections.length} safety detection(s)`);
    }
    visionFaces    = ocrSettled.value.visionFaces;
    fullText       = ocrSettled.value.fullText;
    ocrWords       = ocrSettled.value.words;
    visionLabels   = ocrSettled.value.labels;
    aiDescription  = ocrSettled.value.aiDescription || '';
    if (ocrSettled.value.diagnostics) {
      diagnostics = ocrSettled.value.diagnostics;
    }
    console.info(
      `[Pipeline] OCR ✓ → ${ocrSettled.value.detections.length} PII item(s), ` +
      `${visionFaces.length} Vision face(s)`
    );
  } else {
    console.error('[Pipeline] OCR ✗:', ocrSettled.reason);
  }

  // QR detection result
  if (qrSettled.status === 'fulfilled') {
    allDetections.push(...qrSettled.value);
    console.info(`[Pipeline] QR ✓ — ${qrSettled.value.length} code(s)`);
  } else {
    console.warn('[Pipeline] QR ✗:', qrSettled.reason);
  }

  // ── Combine Vision API faces (only when Python backend was unreachable) ────
  // Python V4 (InsightFace + MediaPipe + Haar) handles all face detection.
  // visionFaces only contains entries when Python had no faces AND GCV returned some.
  if (visionFaces.length > 0) {
    allDetections.push(...visionFaces);
    console.info(`[Pipeline] Added ${visionFaces.length} Vision API face(s) (Python backend fallback)`);
  }

  // ── Apply Confidence Thresholds ──────────────────────────────────────────
  // 1. Only show suggestions for confidence > 45%
  // 2. Default to blurring (redacted = true) for confidence > 70%
  // We preserve python backend explicitly marking items as unredacted (e.g. small faces/names)
  let filteredDetections = allDetections
    .filter(det => det.confidence > 45)
    .map(det => {
      const defaultRedacted = det.confidence > 70;
      return {
        ...det,
        redacted: det.redacted !== undefined && !det.redacted ? false : defaultRedacted
      };
    });

  // ── Cluster Text-based PII ─────────────────────────────────────────
  const EXCLUDED_TYPES = ['face', 'qr_code', 'signature'];
  const textDetections = filteredDetections.filter(d => !EXCLUDED_TYPES.includes(d.type));
  const otherDetections = filteredDetections.filter(d => EXCLUDED_TYPES.includes(d.type));

  // Build clusters
  const EXPAND_PCT = 12; // 12% of width/height
  const clusters: Detection[][] = [];
  const visited = new Set<string>();

  for (const det of textDetections) {
    if (visited.has(det.id)) continue;
    
    // Start a new cluster
    const cluster = [det];
    visited.add(det.id);

    // Iteratively find all connected detections
    let added = true;
    while (added) {
      added = false;
      for (const other of textDetections) {
        if (visited.has(other.id)) continue;

        // Check if `other` intersects with ANY item in the current cluster (using expanded bounding boxes)
        const intersects = cluster.some(cDet => {
          const cx = cDet.bbox.x - EXPAND_PCT;
          const cy = cDet.bbox.y - EXPAND_PCT;
          const cw = cDet.bbox.width + EXPAND_PCT * 2;
          const ch = cDet.bbox.height + EXPAND_PCT * 2;

          const ox = other.bbox.x - EXPAND_PCT;
          const oy = other.bbox.y - EXPAND_PCT;
          const ow = other.bbox.width + EXPAND_PCT * 2;
          const oh = other.bbox.height + EXPAND_PCT * 2;

          return !(cx + cw < ox || cx > ox + ow || cy + ch < oy || cy > oy + oh);
        });

        if (intersects) {
          cluster.push(other);
          visited.add(other.id);
          added = true;
        }
      }
    }
    clusters.push(cluster);
  }

  const clusteredTextDetections: Detection[] = [];
  for (const cluster of clusters) {
    if (cluster.length >= 3) {
      // Merge into a single composite block
      let minX = 100, minY = 100, maxX = 0, maxY = 0;
      let maxConf = 0;

      for (const det of cluster) {
        minX = Math.min(minX, det.bbox.x);
        minY = Math.min(minY, det.bbox.y);
        maxX = Math.max(maxX, det.bbox.x + det.bbox.width);
        maxY = Math.max(maxY, det.bbox.y + det.bbox.height);
        maxConf = Math.max(maxConf, det.confidence);
      }

      clusteredTextDetections.push({
        id: `pii-cluster-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        type: 'address' as any, // General block
        label: 'Address Block (Clustered PII)',
        text: '[REDACTED CLUSTER]',
        confidence: maxConf,
        bbox: {
          x: minX,
          y: minY,
          width: maxX - minX,
          height: maxY - minY,
        },
        redacted: true,
      });
    } else {
      // Keep individual
      clusteredTextDetections.push(...cluster);
    }
  }

  filteredDetections = [...otherDetections, ...clusteredTextDetections];

  allDetections.length = 0;
  allDetections.push(...filteredDetections);

  // ── Step 3.5: LLM Context Validation (eliminates false positives) ───────────
  // Only validate text-based PII; faces/QR/signatures are always kept.
  const VALIDATE_EXCLUDED = ['face', 'qr_code', 'signature', 'illegal_item', 'nudity'];
  const detectionsToValidate = allDetections.filter(d => !VALIDATE_EXCLUDED.includes(d.type));
  const detectionsToKeep    = allDetections.filter(d =>  VALIDATE_EXCLUDED.includes(d.type));

  if (detectionsToValidate.length > 0 && fullText.trim().length > 0) {
    try {
      const baseUrl = typeof window !== 'undefined'
        ? window.location.origin
        : (process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000');

      const validateRes = await fetch(`${baseUrl}/api/validate-detections`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fullText,
          detections: detectionsToValidate.map(d => ({
            id: d.id,
            type: d.type,
            label: d.label,
            text: d.text || '',
          })),
        }),
        signal: AbortSignal.timeout(10000),
      });

      if (validateRes.ok) {
        const { validated } = await validateRes.json();
        const keepSet = new Set<string>(
          (validated || []).filter((v: any) => v.keep).map((v: any) => v.id)
        );
        const removedIds = (validated || []).filter((v: any) => !v.keep).map((v: any) => v.id);
        if (removedIds.length > 0) {
          console.info(`[Pipeline] LLM validation removed ${removedIds.length} false positives:`, removedIds);
        }
        // Only keep text detections that Gemini approved + all face/QR/etc
        const validatedText = detectionsToValidate.filter(d => keepSet.has(d.id));
        allDetections.length = 0;
        allDetections.push(...detectionsToKeep, ...validatedText);
      }
    } catch (validationErr: any) {
      console.warn('[Pipeline] LLM validation skipped (non-fatal):', validationErr.message);
      // Keep all detections as-is if validation fails
    }
  }


  let docType = 'Unknown Document';
  try {
    const { classifyDocument } = await import('./document-classifier');
    docType = classifyDocument(fullText, visionLabels);
    pipelineStatus.documentClassifier = 'success';
    console.info(`[Pipeline] Document type: ${docType}`);
  } catch (e) {
    console.warn('[Pipeline] Document classifier ✗:', e);
    pipelineStatus.documentClassifier = 'failed';
  }

  // ── Step 5: Risk scoring ─────────────────────────────────────────────────
  let privacyScore = 100;
  for (const det of allDetections) {
    const lbl = det.label.toLowerCase();
    if      (lbl.includes('aadhaar'))                              privacyScore -= 40;
    else if (lbl.includes('password') || lbl.includes('credential')) privacyScore -= 35;
    else if (lbl.includes('pan'))                                   privacyScore -= 30;
    else if (lbl.includes('credit') || lbl.includes('debit'))      privacyScore -= 30;
    else if (lbl.includes('bank'))                                  privacyScore -= 25;
    else if (lbl.includes('address'))                               privacyScore -= 20;
    else if (lbl.includes('face'))                                  privacyScore -= 15;
    else if (lbl.includes('phone') || lbl.includes('email'))       privacyScore -= 10;
    else if (lbl.includes('qr'))                                    privacyScore -= 10;
    else                                                            privacyScore -= 5;
  }
  if (docType !== 'Unknown Document') privacyScore -= 10;
  privacyScore = Math.max(0, Math.min(100, privacyScore));

  const riskLevel = scoreToRiskLevel(privacyScore);

  // ── Step 6: Generate redacted image from ALL successful detections ────────
  const redactable = allDetections.filter(d => d.redacted && d.bbox.width > 0);
  const safeImageUrl = await generateSafeImage(fileBlob, redactable, imgW, imgH);

  const processingTime = Math.round(performance.now() - t0);

  console.info(
    `[Pipeline] Complete in ${processingTime}ms — score: ${privacyScore}, risk: ${riskLevel}, ` +
    `detections: ${allDetections.length} | ` +
    `face=${pipelineStatus.face} ocr=${pipelineStatus.ocr} qr=${pipelineStatus.qr}`
  );

  return {
    id:             `scan-${uuid()}`,
    originalUrl:    file.previewUrl,
    safeUrl:        safeImageUrl,
    privacyScore,
    riskLevel,
    detections:     allDetections,
    documentType:   docType,
    ocrWords,
    aiDescription,
    processingTime,
    completedAt:    new Date(),
    recommendations: generateRecommendations(allDetections, pipelineStatus),
    resolution:     `${imgW}×${imgH}`,
    size:           (fileBlob.size / 1024).toFixed(1) + ' KB',
    pipelineStatus,
    diagnostics,
  };
}
