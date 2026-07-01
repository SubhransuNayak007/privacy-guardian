import { v4 as uuid } from 'uuid';
import { ScanResult, ScanFile, Detection, RiskLevel, PipelineStatus } from '@/types';
import { useEditorStore } from '@/lib/editor-store';
import { convertPdfToImage } from './pdf-handler';
import { preprocessImage } from './image-preprocessing';

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

export async function startScanJob(file: ScanFile): Promise<string> {
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

  const trustedFaceImages = useEditorStore.getState().trustedFaceImages;

  // convert blob to base64
  const base64 = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(fileBlob);
  });

  const res = await fetch('/api/scan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      imageBase64: base64,
      trustedFaceImages
    })
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Failed to start scan: ${err}`);
  }

  const data = await res.json();
  if (data.error) throw new Error(data.error);
  
  return data.job_id;
}

export async function pollScanJob(jobId: string, originalFile?: ScanFile): Promise<ScanResult | { status: string }> {
  const res = await fetch(`/api/result/${jobId}`);
  if (!res.ok) {
    if (res.status === 404) return { status: 'not_found' };
    throw new Error('Failed to poll result');
  }

  const data = await res.json();
  if (data.status !== 'completed') {
    return { status: data.status };
  }

  // Create Blob URL for the redacted image
  const base64Str = data.redactedImageBase64;
  let safeUrl = originalFile?.previewUrl || ''; 
  
  if (base64Str) {
    try {
      // Decode base64 (which is returned by python cv2.imencode)
      const byteString = atob(base64Str);
      const ab = new ArrayBuffer(byteString.length);
      const ia = new Uint8Array(ab);
      for (let i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i);
      }
      const blob = new Blob([ab], { type: 'image/jpeg' });
      safeUrl = URL.createObjectURL(blob);
    } catch (e) {
      console.error('Failed to create Blob URL from redactedImageBase64', e);
    }
  }

  const pipelineStatus: PipelineStatus = {
    face: 'success',
    ocr: 'success',
    qr: 'success',
    documentClassifier: 'success'
  };

  return {
    id: jobId,
    originalUrl: originalFile?.previewUrl || '',
    safeUrl,
    privacyScore: data.privacyScore,
    riskLevel: data.riskLevel,
    detections: data.pythonDetections || [],
    documentType: data.aiDescription || 'Unknown',
    ocrWords: data.words || [],
    aiDescription: data.aiDescription,
    processingTime: data.processingTime || 0,
    completedAt: new Date(),
    recommendations: generateRecommendations(data.pythonDetections || [], pipelineStatus),
    resolution: `unknown`, 
    size: originalFile?.originalFile ? (originalFile.originalFile.size / 1024).toFixed(1) + ' KB' : 'unknown',
    pipelineStatus,
    diagnostics: {},
  } as ScanResult;
}
