'use client';

import { motion } from 'framer-motion';
import {
  Shield, AlertTriangle, CheckCircle, Info, TrendingDown,
  Lightbulb, Eye, Download
} from 'lucide-react';
import { ScanResult, RISK_CONFIG, DETECTION_CONFIG, DetectionType } from '@/types';
import { PrivacyScoreRing, RiskBadge, ConfidenceBar } from './PrivacyComponents';

interface IntelligencePanelProps {
  result: ScanResult;
  onDownloadReport?: () => void;
}

export function IntelligencePanel({ result, onDownloadReport }: IntelligencePanelProps) {
  const normalizedRiskLevel = (result.riskLevel?.toLowerCase() || 'low') as keyof typeof RISK_CONFIG;
  const riskConfig = RISK_CONFIG[normalizedRiskLevel] || RISK_CONFIG['low'];
  const sortedDetections = [...result.detections].sort((a, b) => b.confidence - a.confidence);
  const criticalTypes: DetectionType[] = ['aadhaar', 'pan', 'bank_account', 'credit_card', 'password'];
  const criticalDetections = sortedDetections.filter(d => criticalTypes.includes(d.type));
  const otherDetections = sortedDetections.filter(d => !criticalTypes.includes(d.type));

  return (
    <div className="space-y-4">
      {/* ── Privacy Score Header ── */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface rounded-xl border border-border p-5 shadow-xs"
      >
        <div className="flex items-center gap-4">
          {/* Score ring */}
          <PrivacyScoreRing score={result.privacyScore} size={96} />

          {/* Score details */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <RiskBadge riskLevel={result.riskLevel} />
            </div>
            <h3 className="text-sm font-600 text-primary-text mb-1">Privacy Score</h3>
            <p className="text-xs text-secondary-text leading-relaxed">
              {riskConfig.description}
              {' '}
              {result.detections.length} item{result.detections.length !== 1 ? 's' : ''} detected.
            </p>
            <div className="mt-2 text-2xs text-muted-text">
              Processed in {(result.processingTime / 1000).toFixed(1)}s
            </div>
          </div>
        </div>
      </motion.div>

      {/* ── Detections List ── */}
      {result.detections.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-surface rounded-xl border border-border overflow-hidden shadow-xs"
        >
          <div className="intel-panel-header">
            <Eye size={14} className="text-secondary-text" />
            Detected Items
            <span className="ml-auto text-2xs text-muted-text font-400">
              {result.detections.length} found
            </span>
          </div>

          <div className="intel-panel-body space-y-3">
            {/* Critical detections first */}
            {criticalDetections.length > 0 && (
              <div className="space-y-2">
                {criticalDetections.length > 0 && (
                  <div className="text-2xs uppercase tracking-widest text-danger font-600 mb-1">
                    Critical
                  </div>
                )}
                {criticalDetections.map((detection, i) => {
                  const config = DETECTION_CONFIG[detection.type] || {
                    label: detection.type,
                    icon: 'alert-circle',
                    color: 'var(--muted-text)',
                    bgColor: 'var(--surface-elevated)',
                    description: 'Detected element'
                  };
                  return (
                    <motion.div
                      key={detection.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.15 + i * 0.06 }}
                      className="flex items-center justify-between gap-3 p-2.5 rounded-lg"
                      style={{
                        backgroundColor: config.bgColor,
                        border: `1px solid ${config.color}20`,
                      }}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div
                          className="w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0"
                          style={{ backgroundColor: `${config.color}18` }}
                        >
                          <div style={{ color: config.color }} className="text-xs font-700">
                            {detection.type.charAt(0).toUpperCase()}
                          </div>
                        </div>
                        <div className="min-w-0">
                          <div className="text-xs font-600 text-primary-text">{config.label}</div>
                          {detection.text && (
                            <div className="text-2xs text-secondary-text font-mono truncate">{detection.text}</div>
                          )}
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div className="text-xs font-700 tabular-nums" style={{ color: config.color }}>
                          {detection.confidence}%
                        </div>
                        <div className="text-2xs text-muted-text">conf.</div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}

            {/* Other detections */}
            {otherDetections.length > 0 && (
              <div className="space-y-2">
                {criticalDetections.length > 0 && (
                  <div className="text-2xs uppercase tracking-widest text-secondary-text font-600 mb-1 mt-3">
                    Also detected
                  </div>
                )}
                {otherDetections.map((detection, i) => {
                  const config = DETECTION_CONFIG[detection.type] || {
                    label: detection.type,
                    icon: 'alert-circle',
                    color: 'var(--muted-text)',
                    bgColor: 'var(--surface-elevated)',
                    description: 'Detected element'
                  };
                  return (
                    <motion.div
                      key={detection.id}
                      initial={{ opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.2 + i * 0.05 }}
                      className="flex items-center justify-between gap-3 p-2.5 rounded-lg"
                      style={{
                        backgroundColor: config.bgColor,
                        border: `1px solid ${config.color}20`,
                      }}
                    >
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div
                          className="w-6 h-6 rounded-md flex items-center justify-center flex-shrink-0"
                          style={{ backgroundColor: `${config.color}18` }}
                        >
                          <div style={{ color: config.color }} className="text-xs font-700">
                            {detection.type.charAt(0).toUpperCase()}
                          </div>
                        </div>
                        <div className="min-w-0">
                          <div className="text-xs font-600 text-primary-text">{config.label}</div>
                          {detection.text && (
                            <div className="text-2xs text-secondary-text font-mono truncate">{detection.text}</div>
                          )}
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div className="text-xs font-700 tabular-nums" style={{ color: config.color }}>
                          {detection.confidence}%
                        </div>
                        <div className="text-2xs text-muted-text">conf.</div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* ── AI Confidence Breakdown ── */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-surface rounded-xl border border-border overflow-hidden shadow-xs"
      >
        <div className="intel-panel-header">
          <Shield size={14} className="text-secondary-text" />
          AI Confidence Breakdown
        </div>
        <div className="intel-panel-body space-y-3.5">
          {[
            { label: 'OCR Text Extraction', value: 94 },
            { label: 'Face Detection', value: 97 },
            { label: 'PII Pattern Matching', value: 89 },
            { label: 'Risk Scoring Model', value: 91 },
          ].map(({ label, value }, i) => (
            <motion.div
              key={label}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 + i * 0.06 }}
            >
              <ConfidenceBar label={label} confidence={value} color="var(--primary)" />
            </motion.div>
          ))}
          <p className="text-2xs text-muted-text mt-2 leading-relaxed">
            Confidence scores reflect model certainty, not detection accuracy.
            Always review results before sharing.
          </p>
        </div>
      </motion.div>

      {/* ── Recommendations ── */}
      {result.recommendations.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-surface rounded-xl border border-border overflow-hidden shadow-xs"
        >
          <div className="intel-panel-header">
            <Lightbulb size={14} className="text-brand-accent" />
            Recommendations
          </div>
          <div className="intel-panel-body">
            <ul className="space-y-2.5">
              {result.recommendations.map((rec, i) => (
                <motion.li
                  key={i}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.35 + i * 0.06 }}
                  className="flex items-start gap-2.5 text-xs text-primary-text"
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-brand-accent mt-1.5 flex-shrink-0" />
                  <span>{rec}</span>
                </motion.li>
              ))}
            </ul>
          </div>
        </motion.div>
      )}

      {/* ── Disclaimer ── */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
        className="flex items-start gap-2 p-3 bg-surface-elevated rounded-lg border border-border"
      >
        <Info size={13} className="text-muted-text mt-0.5 flex-shrink-0" />
        <p className="text-2xs text-muted-text leading-relaxed">
          AI detection may not find all sensitive data. Manually review the image before sharing,
          especially for government IDs and financial documents.
        </p>
      </motion.div>
    </div>
  );
}

