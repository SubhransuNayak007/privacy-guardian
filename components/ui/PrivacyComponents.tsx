'use client';

import { motion } from 'framer-motion';
import {
  Phone, Mail, Fingerprint, CreditCard, Landmark, Key,
  QrCode, MapPin, User, UserCheck, PenLine, AlertTriangle,
  CheckCircle, AlertCircle, XCircle, Car, EyeOff, Zap,
  FileText, FileHeart, FileBarChart, Package, Calendar,
  BookOpen, Smartphone, Shield
} from 'lucide-react';
import { Detection, DetectionType, RiskLevel, getDetectionConfig, RISK_CONFIG } from '@/types';

// ───────────────────────────────────────────
// Detection Badge
// ───────────────────────────────────────────
const ICON_MAP: Record<string, React.ElementType> = {
  // Lucide icon name -> component
  phone:             Phone,
  mail:              Mail,
  fingerprint:       Fingerprint,
  'credit-card':     CreditCard,
  landmark:          Landmark,
  key:               Key,
  'qr-code':         QrCode,
  'map-pin':         MapPin,
  user:              User,
  'user-check':      UserCheck,
  'pen-line':        PenLine,
  'alert-triangle':  AlertTriangle,
  'check-circle':    CheckCircle,
  'alert-circle':    AlertCircle,
  'x-circle':        XCircle,
  car:               Car,
  'eye-off':         EyeOff,
  zap:               Zap,
  'file-text':       FileText,
  'file-heart':      FileHeart,
  'file-bar-chart':  FileBarChart,
  package:           Package,
  calendar:          Calendar,
  'book-open':       BookOpen,
  smartphone:        Smartphone,
  shield:            Shield,
};

interface DetectionBadgeProps {
  detection: Detection;
  showConfidence?: boolean;
  size?: 'sm' | 'md';
}

export function DetectionBadge({ detection, showConfidence = true, size = 'md' }: DetectionBadgeProps) {
  const config = getDetectionConfig(detection.type);
  const Icon = ICON_MAP[config.icon] ?? AlertTriangle;

  // Pulse animation for NSFW detections
  const isHighPriority = detection.type === 'nsfw' || detection.type === 'weapon';

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`flex items-center justify-between gap-3 rounded-xl border ${
        size === 'sm' ? 'p-2.5' : 'p-3'
      } ${isHighPriority ? 'ring-1' : ''}`}
      style={{
        backgroundColor: config.bgColor,
        borderColor: `${config.color}35`,
        ...(isHighPriority ? { ringColor: config.color } : {}),
      }}
    >
      <div className="flex items-center gap-2.5">
        <div
          className="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: `${config.color}20` }}
        >
          <Icon size={14} style={{ color: config.color }} />
        </div>
        <div>
          <div className="text-sm font-600 text-primary-text leading-none mb-0.5">
            {config.label}
          </div>
          {detection.text && detection.type !== 'nsfw' && (
            <div className="text-xs text-secondary-text font-mono">
              {detection.text.startsWith('[') ? '' : detection.text}
            </div>
          )}
          {detection.type === 'nsfw' && (
            <div className="text-xs" style={{ color: config.color }}>
              Auto-blurred for privacy
            </div>
          )}
        </div>
      </div>

      {showConfidence && (
        <div className="text-right flex-shrink-0">
          <div className="text-xs font-700" style={{ color: config.color }}>
            {Math.round(detection.confidence)}%
          </div>
          <div className="text-[10px] text-muted-text">confidence</div>
        </div>
      )}
    </motion.div>
  );
}

// ───────────────────────────────────────────
// Risk Badge
// ───────────────────────────────────────────
export function RiskBadge({ riskLevel }: { riskLevel: RiskLevel }) {
  const config = RISK_CONFIG[riskLevel];
  const Icon = riskLevel === 'low' ? CheckCircle
    : riskLevel === 'medium' ? AlertTriangle
    : riskLevel === 'high' ? AlertCircle
    : XCircle;

  return (
    <span
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-600 border"
      style={{
        color: config.color,
        backgroundColor: config.bgColor,
        borderColor: `${config.borderColor}40`,
      }}
    >
      <Icon size={12} />
      {config.label}
    </span>
  );
}

// ───────────────────────────────────────────
// Privacy Score Ring
// ───────────────────────────────────────────
interface PrivacyScoreProps {
  score: number;
  size?: number;
}

export function PrivacyScoreRing({ score, size = 120 }: PrivacyScoreProps) {
  const radius = (size - 16) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const color = score >= 80 ? 'var(--success)'
    : score >= 50 ? 'var(--warning)'
    : score >= 25 ? 'var(--danger)'
    : 'var(--danger)';

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      {/* Background ring */}
      <svg width={size} height={size} className="absolute inset-0 -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--border)"
          strokeWidth="8"
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: 'easeOut', delay: 0.3 }}
        />
      </svg>
      {/* Score text */}
      <div className="text-center z-10">
        <motion.div
          initial={{ opacity: 0, scale: 0.5 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.6, duration: 0.4 }}
          className="text-2xl font-800 text-primary-text leading-none"
        >
          {score}
        </motion.div>
        <div className="text-[10px] text-secondary-text font-500 mt-0.5">/ 100</div>
      </div>
    </div>
  );
}

// ───────────────────────────────────────────
// Confidence Bar
// ───────────────────────────────────────────
export function ConfidenceBar({
  label,
  confidence,
  color = 'var(--primary)',
}: {
  label: string;
  confidence: number;
  color?: string;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <span className="text-sm text-primary-text font-500">{label}</span>
        <span className="text-sm font-700 tabular-nums" style={{ color }}>
          {confidence}%
        </span>
      </div>
      <div className="h-1.5 bg-brand-border rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${confidence}%` }}
          transition={{ duration: 1, ease: 'easeOut', delay: 0.2 }}
          className="h-full rounded-full"
          style={{ background: `linear-gradient(90deg, ${color}, ${color}CC)` }}
        />
      </div>
    </div>
  );
}

// ───────────────────────────────────────────
// Processing Stage Item
// ───────────────────────────────────────────
export function StageItem({
  label,
  status,
  progress,
  delay = 0,
}: {
  label: string;
  status: 'pending' | 'active' | 'done';
  progress?: number;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.3 }}
      className={`flex items-center gap-4 p-4 rounded-xl transition-all duration-300 ${
        status === 'active' ? 'bg-primary/5 border border-primary/20' :
        status === 'done' ? 'bg-surface/60' : 'opacity-40'
      }`}
    >
      {/* Status icon */}
      <div className="flex-shrink-0 w-7 h-7">
        {status === 'done' && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 400, damping: 20 }}
            className="w-7 h-7 rounded-full bg-primary flex items-center justify-center"
          >
            <CheckCircle size={14} className="text-background" />
          </motion.div>
        )}
        {status === 'active' && (
          <div className="w-7 h-7 rounded-full border-2 border-primary border-t-transparent animate-spin" />
        )}
        {status === 'pending' && (
          <div className="w-7 h-7 rounded-full border-2 border-border" />
        )}
      </div>

      <div className="flex-1 min-w-0">
        <div className={`text-sm font-500 ${
          status === 'done' ? 'text-primary-text line-through opacity-60' :
          status === 'active' ? 'text-primary font-600' : 'text-secondary-text'
        }`}>
          {status === 'done' ? `✓ ${label.replace('...', '')}` : label}
        </div>

        {status === 'active' && progress !== undefined && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-2"
          >
            <div className="h-1 bg-brand-border rounded-full overflow-hidden">
              <motion.div
                initial={{ width: '0%' }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3 }}
                className="h-full rounded-full bg-gradient-to-r from-primary to-primary-light"
              />
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}

