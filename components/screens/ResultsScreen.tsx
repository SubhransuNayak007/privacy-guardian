'use client';

import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft, Download, FileDown, RotateCcw, PenLine,
  Plus, Share2, CheckCircle, AlertCircle, Shield
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { ComparisonSlider } from '@/components/ui/ComparisonSlider';
import { IntelligencePanel } from '@/components/ui/IntelligencePanel';
import { RiskBadge } from '@/components/ui/PrivacyComponents';
import { formatFileSize } from '@/lib/utils';
import DebugPanel from '@/components/screens/DebugPanel';

interface ResultsScreenProps {
  scanId: string;
}

export function ResultsScreen({ scanId }: ResultsScreenProps) {
  const router = useRouter();
  const { currentResult, currentFile, resetScan, setFile, setResult } = useAppStore();
  const [downloadState, setDownloadState] = useState<'idle' | 'loading' | 'done'>('idle');
  const [reportState, setReportState] = useState<'idle' | 'loading' | 'done'>('idle');
  const [isLoadingSession, setIsLoadingSession] = useState(true);

  const result = currentResult;
  const file = currentFile;

  useEffect(() => {
    async function loadScanSession(id: string) {
      if (!result || !file) {
        try {
          const { getScanSession } = await import('@/lib/idb');
          const session = await getScanSession(id);
          if (session && session.result && session.fileMetadata && session.fileDataUrl) {
            const reconstructedFile = {
              ...session.fileMetadata,
              originalFile: new File([], session.fileMetadata.name, { type: session.fileMetadata.type }),
              previewUrl: session.fileDataUrl
            };
            setFile(reconstructedFile as any);
            
            // The saved result.originalUrl is a transient blob URL which is now dead.
            // We must patch it to use the persistent base64 fileDataUrl.
            const patchedResult = { 
              ...session.result,
              originalUrl: session.fileDataUrl 
            };
            setResult(patchedResult);
          } else {
            router.push('/');
          }
        } catch {
          router.push('/');
        }
      }
      setIsLoadingSession(false);
    }
    
    if (!result || !file) {
      loadScanSession(scanId);
    } else {
      setIsLoadingSession(false);
    }
  }, [result, file, router, scanId, setFile, setResult]);

  if (!result || !file) {
    if (isLoadingSession) {
      return (
        <div className="min-h-[calc(100vh-64px)] flex items-center justify-center">
          <div className="w-8 h-8 rounded-full border-4 border-primary/30 border-t-primary animate-spin" />
        </div>
      );
    }
    return null;
  }

  const handleDownloadSafe = async () => {
    setDownloadState('loading');
    await new Promise(r => setTimeout(r, 800)); // simulate download prep
    // In production: trigger pre-signed R2 URL download
    const link = document.createElement('a');
    link.href = result.safeUrl || result.originalUrl;
    link.download = `safe_${file.name}`;
    link.click();
    setDownloadState('done');
    setTimeout(() => setDownloadState('idle'), 2500);
  };

  const handleExportReport = async () => {
    setReportState('loading');

    try {
      // Dynamic import to keep bundle small
      const { exportPDFReport } = await import('@/lib/pdf-export');
      await exportPDFReport(result, file);
      setReportState('done');
      setTimeout(() => setReportState('idle'), 2500);
    } catch (err) {
      console.error('PDF export failed:', err);
      setReportState('idle');
    }
  };

  const handleScanAnother = () => {
    resetScan();
    router.push('/');
  };

  const handleRetry = () => {
    router.push(`/scanning/${scanId}`);
  };

  const handleEdit = () => {
    router.push(`/results/${scanId}/edit`);
  };

  const score = result.riskScore !== undefined ? result.riskScore : (100 - result.privacyScore);
  const scoreColor = score <= 20 ? 'var(--success)'
    : score <= 50 ? 'var(--warning)'
    : score <= 80 ? 'var(--danger)'
    : 'var(--danger)';

  return (
    <div className="min-h-[calc(100vh-64px)] px-4 py-8">
      <div className="max-w-7xl mx-auto">

        {/* ── Top bar ── */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-6 flex-wrap gap-3"
        >
          <button
            id="results-back"
            onClick={() => router.push('/')}
            className="flex items-center gap-1.5 text-sm text-secondary-text hover:text-primary-text transition-colors min-h-[44px] min-w-[44px]"
          >
            <ArrowLeft size={15} />
            New scan
          </button>

          <div className="flex items-center gap-2 flex-wrap">
            <RiskBadge riskLevel={result.riskLevel} />
            <span className="text-xs text-muted-text">
              {result.detections.length} item{result.detections.length !== 1 ? 's' : ''} detected in {(result.processingTime / 1000).toFixed(1)}s
            </span>
          </div>

          {/* Export PDF — primary action in header */}
          <motion.button
            id="export-pdf-header"
            onClick={handleExportReport}
            disabled={reportState === 'loading'}
            className="btn-premium py-1.5 px-3 text-sm min-h-[44px] min-w-[44px]"
          >
            {reportState === 'loading' ? (
              <div className="w-3.5 h-3.5 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
            ) : reportState === 'done' ? (
              <CheckCircle size={14} className="text-success" />
            ) : (
              <FileDown size={14} />
            )}
            {reportState === 'done' ? 'Report saved!' : 'Export Report'}
          </motion.button>
        </motion.div>

        {/* ── Main layout ── */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_380px] gap-6">

          {/* ── LEFT: Comparison + Actions ── */}
          <div className="space-y-4">
            {/* Filename + score pill */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center gap-3 flex-wrap"
            >
              <div className="flex items-center gap-2 min-w-0">
                <Shield size={16} className="text-primary flex-shrink-0" />
                <span className="text-sm font-600 text-primary-text truncate">{file.name}</span>
                <span className="text-xs text-muted-text flex-shrink-0">{formatFileSize(file.size)}</span>
              </div>
              <div
                className="ml-auto flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-700 border"
                style={{
                  color: scoreColor,
                  backgroundColor: `color-mix(in srgb, ${scoreColor} 10%, transparent)`,
                  borderColor: `color-mix(in srgb, ${scoreColor} 30%, transparent)`,
                }}
              >
                Risk score: {score}/100
              </div>
            </motion.div>

            {/* Comparison slider */}
            <motion.div
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ type: "spring", stiffness: 150, damping: 20 }}
              className="rounded-2xl overflow-hidden border border-border shadow-card"
              style={{ minHeight: '320px', maxHeight: '560px' }}
            >
              <ComparisonSlider
                originalSrc={result.originalUrl}
                safeSrc={result.safeUrl || result.originalUrl}
                alt={`Privacy comparison for ${file.name}`}
                className="w-full"
              />
            </motion.div>

            {/* Slider hint */}
            <p className="text-center text-xs text-muted-text">
              ← Drag to compare Original vs Safe version →
            </p>

            {/* Action buttons */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ type: "spring", stiffness: 150, damping: 20, delay: 0.15 }}
              className="grid grid-cols-2 sm:grid-cols-4 gap-2.5"
            >
              {/* Download safe image */}
              <ActionButton
                id="download-safe"
                icon={Download}
                label={downloadState === 'done' ? 'Downloaded!' : 'Download Safe'}
                onClick={handleDownloadSafe}
                loading={downloadState === 'loading'}
                done={downloadState === 'done'}
                variant="primary"
              />

              {/* Export PDF */}
              <ActionButton
                id="export-pdf-main"
                icon={FileDown}
                label={reportState === 'done' ? 'Saved!' : 'Export PDF'}
                onClick={handleExportReport}
                loading={reportState === 'loading'}
                done={reportState === 'done'}
                variant="secondary"
              />

              {/* Edit manually */}
              <ActionButton
                id="edit-blur"
                icon={PenLine}
                label="Edit Blur"
                onClick={handleEdit}
                variant="secondary"
              />

              {/* Retry scan */}
              <ActionButton
                id="retry-scan"
                icon={RotateCcw}
                label="Re-scan"
                onClick={handleRetry}
                variant="ghost"
              />
            </motion.div>

            {/* Scan another — secondary CTA */}
            <motion.button
              id="scan-another"
              onClick={handleScanAnother}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="w-full flex items-center justify-center gap-2 text-sm text-primary font-600 border border-primary/20 hover:bg-primary/5 rounded-xl py-3 min-h-[44px] transition-all duration-300 hover:shadow-soft hover:-translate-y-0.5 glass-panel"
            >
              <Plus size={15} />
              Scan another image
            </motion.button>

            {/* Detection summary on mobile */}
            <div className="lg:hidden">
              <IntelligencePanel result={result} onDownloadReport={handleExportReport} />
            </div>
          </div>

          {/* ── RIGHT: Intelligence panel (desktop) ── */}
          <motion.div
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="hidden lg:block space-y-4"
          >
            <IntelligencePanel result={result} onDownloadReport={handleExportReport} />
          </motion.div>
        </div>
      </div>
      <DebugPanel />
    </div>
  );
}

// ── Shared action button ──────────────────────────────────────
function ActionButton({
  id,
  icon: Icon,
  label,
  onClick,
  loading = false,
  done = false,
  variant = 'secondary',
}: {
  id: string;
  icon: React.ElementType;
  label: string;
  onClick: () => void;
  loading?: boolean;
  done?: boolean;
  variant?: 'primary' | 'secondary' | 'ghost';
}) {
  const base = 'flex flex-col items-center gap-1.5 p-3 rounded-xl text-xs transition-all duration-300 disabled:opacity-60';

  const variants = {
    primary: 'bg-gradient-to-b from-primary/90 to-primary text-background hover:from-primary-light/90 hover:to-primary-light shadow-cta hover:shadow-primary-glow border border-primary-light/20 hover:-translate-y-1',
    secondary: 'bg-surface border border-border text-primary-text hover:shadow-card hover:-translate-y-0.5',
    ghost: 'text-secondary-text hover:text-primary-text hover:bg-surface hover:border hover:border-border hover:shadow-soft',
  };

  return (
    <button
      id={id}
      onClick={onClick}
      disabled={loading}
      className={`${base} ${variants[variant]} font-600 active:scale-95`}
    >
      {loading ? (
        <div className="w-4 h-4 rounded-full border-2 border-current/30 border-t-current animate-spin" />
      ) : done ? (
        <CheckCircle size={16} className={variant === 'primary' ? 'text-background' : 'text-success'} />
      ) : (
        <Icon size={16} />
      )}
      <span className="truncate w-full text-center">{label}</span>
    </button>
  );
}

