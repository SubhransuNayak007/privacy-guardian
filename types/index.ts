// types/index.ts — Core domain types for Privacy Guardian

export type ScanStatus = 'idle' | 'uploading' | 'scanning' | 'complete' | 'error';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export type DetectionType =
  | 'phone'
  | 'email'
  | 'aadhaar'
  | 'pan'
  | 'bank_account'
  | 'password'
  | 'qr_code'
  | 'barcode'
  | 'address'
  | 'face'
  | 'credit_card'
  | 'name'
  | 'signature'
  | 'dob'
  | 'passport'
  | 'voter_id'
  | 'dl'
  | 'pincode'
  | 'gstin'
  | 'upi'
  | 'nsfw'             // NudeNet — exposed body parts
  | 'weapon'           // YOLO — knife, gun, etc.
  | 'license_plate'    // ALPR / regex
  | 'tracking'         // courier tracking numbers
  | 'document_medical' // medical prescription / report
  | 'document_legal'   // legal agreements, court orders
  | 'document_financial' // invoices, receipts
  | string;            // fallback for any new types from backend


export interface BoundingBox {
  x: number;       // percentage 0–100
  y: number;
  width: number;
  height: number;
}

export interface Detection {
  id: string;
  type: DetectionType;
  label: string;
  confidence: number; // 0–100, never exactly 100
  bbox: BoundingBox;
  polygon?: { x: number; y: number }[]; // For SAM segmentation
  text?: string;      // partially masked, for display
  redacted: boolean;
}

export interface ScanFile {
  id: string;
  name: string;
  size: number;
  dimensions: { width: number; height: number };
  type: string;
  previewUrl: string;
  uploadedAt: Date;
  originalFile?: File;
}

/** Status reported per-pipeline after a parallel scan */
export interface PipelineStatus {
  face:               'running' | 'success' | 'failed' | 'skipped';
  ocr:                'running' | 'success' | 'failed' | 'skipped';
  qr:                 'running' | 'success' | 'failed' | 'skipped';
  documentClassifier: 'running' | 'success' | 'failed' | 'skipped';
}

export interface ScanResult {
  id: string;
  file?: ScanFile;           // optional – currentFile is stored separately in store
  originalUrl: string;
  safeUrl: string;
  privacyScore: number;      // 0–100 (higher = safer)
  riskScore?: number;        // 0-100 (higher = riskier)
  riskLevel: RiskLevel;
  detections: Detection[];
  documentType?: string;
  ocrWords?: { text: string }[];
  processingTime: number;    // milliseconds
  completedAt: Date;
  recommendations: string[];
  aiDescription?: string;
  resolution?: string;       // "1920×1080"
  size?: string;             // "512.3 KB"
  pipelineStatus?: PipelineStatus;
  diagnostics?: Record<string, string>;
}

export interface ScanState {
  status: ScanStatus;
  file: ScanFile | null;
  result: ScanResult | null;
  progress: number;          // 0–100
  currentStage: string;
  error: string | null;
}

export interface RecentScan {
  id: string;
  filename: string;
  thumbnail: string;
  privacyScore: number;
  riskLevel: RiskLevel;
  scannedAt: Date;
  detectionCount: number;
}

export interface FaceEnrollment {
  id: string;
  userId: string;
  enrolled: boolean;
  faceCount: number;
  enrolledAt: Date;
}

// ── Detection display config ───────────────────────────────────────────────
export const DETECTION_CONFIG: Record<DetectionType, {
  label: string;
  icon: string;
  color: string;
  bgColor: string;
  description: string;
}> = {
  phone: {
    label: 'Phone Number',
    icon: 'phone',
    color: '#C0392B',
    bgColor: '#FDEDEC',
    description: 'Mobile or landline number detected',
  },
  email: {
    label: 'Email Address',
    icon: 'mail',
    color: '#8E44AD',
    bgColor: '#F5EEF8',
    description: 'Email address detected',
  },
  aadhaar: {
    label: 'Aadhaar Number',
    icon: 'fingerprint',
    color: '#C0392B',
    bgColor: '#FDEDEC',
    description: '12-digit government ID detected',
  },
  pan: {
    label: 'PAN Card',
    icon: 'credit-card',
    color: '#D68910',
    bgColor: '#FEF9E7',
    description: 'PAN card number detected',
  },
  bank_account: {
    label: 'Bank Account',
    icon: 'landmark',
    color: '#C0392B',
    bgColor: '#FDEDEC',
    description: 'Bank account number detected',
  },
  password: {
    label: 'Password Field',
    icon: 'key',
    color: '#C0392B',
    bgColor: '#FDEDEC',
    description: 'Password or PIN detected',
  },
  qr_code: {
    label: 'QR Code',
    icon: 'qr-code',
    color: '#2471A3',
    bgColor: '#EBF5FB',
    description: 'QR code with embedded data detected',
  },
  address: {
    label: 'Address',
    icon: 'map-pin',
    color: '#D68910',
    bgColor: '#FEF9E7',
    description: 'Physical address detected',
  },
  face: {
    label: 'Face',
    icon: 'user',
    color: '#1E8449',
    bgColor: '#EAFAF1',
    description: 'Human face detected',
  },
  credit_card: {
    label: 'Credit Card',
    icon: 'credit-card',
    color: '#C0392B',
    bgColor: '#FDEDEC',
    description: 'Credit/debit card number detected',
  },
  name: {
    label: 'Full Name',
    icon: 'user-check',
    color: '#8E44AD',
    bgColor: '#F5EEF8',
    description: 'Personal name detected',
  },
  signature: {
    label: 'Signature Region',
    icon: 'pen-line',
    color: '#5F6368',
    bgColor: '#F1F3F4',
    description: 'Handwritten signature region detected',
  },
  dob: {
    label: 'Date of Birth',
    icon: 'calendar',
    color: '#C0392B',
    bgColor: '#FDEDEC',
    description: 'Date of birth detected',
  },
  passport: {
    label: 'Passport Number',
    icon: 'book-open',
    color: '#C0392B',
    bgColor: '#FDEDEC',
    description: 'Passport number detected',
  },
  voter_id: {
    label: 'Voter ID',
    icon: 'check-square',
    color: '#D68910',
    bgColor: '#FEF9E7',
    description: 'Voter ID detected',
  },
  pincode: {
    label: 'PIN Code',
    icon: 'map-pin',
    color: '#D68910',
    bgColor: '#FEF9E7',
    description: 'Postal PIN code detected',
  },
  gstin: {
    label: 'GSTIN',
    icon: 'landmark',
    color: '#D68910',
    bgColor: '#FEF9E7',
    description: 'GST Identification Number detected',
  },
  tracking: {
    label: 'Tracking Number',
    icon: 'package',
    color: '#2471A3',
    bgColor: '#EBF5FB',
    description: 'Courier tracking number detected',
  },
  barcode: {
    label: 'Barcode',
    icon: 'qr-code',
    color: '#2471A3',
    bgColor: '#EBF5FB',
    description: 'Barcode with embedded data detected',
  },
  // ── New models ────────────────────────────────────────
  nsfw: {
    label: '🔞 NSFW Content',
    icon: 'eye-off',
    color: '#7B241C',
    bgColor: '#FADBD8',
    description: 'Exposed intimate body part detected — blurred automatically',
  },
  weapon: {
    label: '⚠️ Weapon',
    icon: 'zap',
    color: '#922B21',
    bgColor: '#FDEDEC',
    description: 'Weapon or dangerous object detected',
  },
  license_plate: {
    label: '🚗 License Plate',
    icon: 'car',
    color: '#1A5276',
    bgColor: '#D6EAF8',
    description: 'Vehicle license plate detected',
  },
  document_medical: {
    label: '🏥 Medical Document',
    icon: 'file-heart',
    color: '#117A65',
    bgColor: '#D1F2EB',
    description: 'Medical prescription or report detected',
  },
  document_legal: {
    label: '⚖️ Legal Document',
    icon: 'file-text',
    color: '#4A235A',
    bgColor: '#E8DAEF',
    description: 'Legal agreement or court document detected',
  },
  document_financial: {
    label: '💳 Financial Document',
    icon: 'file-bar-chart',
    color: '#9A7D0A',
    bgColor: '#FEF9E7',
    description: 'Invoice, receipt, or financial record detected',
  },
  // Catch-all for unknown dynamic types
  dl: {
    label: "Driver's License",
    icon: 'id-card',
    color: '#C0392B',
    bgColor: '#FDEDEC',
    description: "Driver's license number detected",
  },
  upi: {
    label: 'UPI ID',
    icon: 'smartphone',
    color: '#8E44AD',
    bgColor: '#F5EEF8',
    description: 'UPI payment ID detected',
  },
};

/** Safe getter — returns a fallback config for unknown backend types */
export function getDetectionConfig(type: string) {
  return (
    (DETECTION_CONFIG as Record<string, typeof DETECTION_CONFIG[DetectionType]>)[type] ?? {
      label: type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      icon: 'alert-triangle',
      color: '#5F6368',
      bgColor: '#F1F3F4',
      description: 'Sensitive data detected',
    }
  );
}

export const RISK_CONFIG: Record<RiskLevel, {
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  description: string;
  scoreRange: string;
}> = {
  low: {
    label: 'Low Risk',
    color: '#1E8449',
    bgColor: '#EAFAF1',
    borderColor: '#1E8449',
    description: 'Minimal sensitive information found.',
    scoreRange: '80–100',
  },
  medium: {
    label: 'Medium Risk',
    color: '#D68910',
    bgColor: '#FEF9E7',
    borderColor: '#D68910',
    description: 'Some sensitive information detected.',
    scoreRange: '50–79',
  },
  high: {
    label: 'High Risk',
    color: '#C0392B',
    bgColor: '#FDEDEC',
    borderColor: '#C0392B',
    description: 'Significant sensitive information found.',
    scoreRange: '20–49',
  },
  critical: {
    label: 'Critical Risk',
    color: '#922B21',
    bgColor: '#FDEDEC',
    borderColor: '#922B21',
    description: 'Multiple critical identifiers exposed.',
    scoreRange: '0–19',
  },
};
