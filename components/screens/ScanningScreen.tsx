'use client';

import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Clock, Lock, CheckCircle, AlertCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { startScanJob, pollScanJob, SCAN_STAGES } from '@/lib/ai/pipeline';
import { saveScanSession, fileToBase64 } from '@/lib/idb';
import type { PipelineStatus } from '@/types';

interface ScanningScreenProps {
  scanId: string;
}

interface Stage {
  id: string;
  label: string;
  duration: number;
  status: 'pending' | 'active' | 'done';
  progress: number;
}

export function ScanningScreen({ scanId }: ScanningScreenProps) {
  const router = useRouter();
  const { currentFile, setResult, scanStatus, setScanStatus, error, setError, addRecentScan } = useAppStore();

  const [stages, setStages] = useState<Stage[]>(
    SCAN_STAGES.map(s => ({ ...s, status: 'pending' as const, progress: 0 }))
  );
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [overallProgress, setOverallProgress] = useState(0);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [scanComplete, setScanComplete] = useState(false);
  const [pipelineStatusState, setPipelineStatusState] = useState<PipelineStatus | null>(null);
  const didStartRef = useRef(false);
  const startTimeRef = useRef<number>(0);
  const didCompleteRef = useRef(false);

  const file = currentFile;

  useEffect(() => {
    if (!file || didStartRef.current) return;
    didStartRef.current = true;
    startTimeRef.current = Date.now();

    const totalDuration = SCAN_STAGES.reduce((sum, s) => sum + s.duration, 0);

    async function animateStages() {
      let elapsed = 0;
      const timer = setInterval(() => {
        setElapsedMs(Date.now() - startTimeRef.current);
      }, 1000);

      for (let i = 0; i < SCAN_STAGES.length; i++) {
        if (didCompleteRef.current) break;

        const stage = SCAN_STAGES[i];
        const stageDuration = stage.duration;

        setCurrentStageIdx(i);
        setStages(prev => prev.map((s, idx) => ({
          ...s,
          status: idx === i ? 'active' : idx < i ? 'done' : 'pending',
          progress: idx === i ? 0 : idx < i ? 100 : 0,
        })));

        // Wait a tick for React to render the active state at 0 progress
        await new Promise(r => setTimeout(r, 50));
        
        if (didCompleteRef.current) break;

        setStages(prev => prev.map((s, idx) =>
          idx === i ? { ...s, progress: 100 } : s
        ));
        
        const overall = Math.round(((elapsed + stageDuration) / totalDuration) * 100);
        setOverallProgress(Math.min(95, overall));

        await new Promise(r => setTimeout(r, stageDuration));
        
        elapsed += stageDuration;
      }
      clearInterval(timer);
    }

    async function runScan() {
      try {
        const animationPromise = animateStages();

        let jobId = localStorage.getItem('lastJobId');
        
        if (!jobId) {
          jobId = await startScanJob(file!);
          localStorage.setItem('lastJobId', jobId);
        }

        let result: any = null;
        while (true) {
          const pollResult = await pollScanJob(jobId, file!);
          if ('status' in pollResult && (pollResult.status === 'not_found' || pollResult.status === 'failed' || pollResult.status === 'error')) {
            localStorage.removeItem('lastJobId');
            jobId = await startScanJob(file!);
            localStorage.setItem('lastJobId', jobId);
          } else if ('id' in pollResult && pollResult.id) {
            result = pollResult;
            break;
          }
          await new Promise(r => setTimeout(r, 1500));
        }

        localStorage.removeItem('lastJobId');
        didCompleteRef.current = true;

        // All stages done
        setOverallProgress(100);
        setStages(prev => prev.map(s => ({ ...s, status: 'done', progress: 100 })));
        setScanComplete(true);

        // Capture pipeline status for display
        if (result.pipelineStatus) {
          setPipelineStatusState(result.pipelineStatus);
        }

        // Store result
        setResult(result);
        setScanStatus('complete');

        // Add to recent scans
        if (file) {
          addRecentScan({
            id: result.id,
            filename: file.name,
            thumbnail: file.previewUrl,
            privacyScore: result.privacyScore,
            riskLevel: result.riskLevel,
            scannedAt: new Date(),
            detectionCount: result.detections.length,
          });

          if (file.originalFile) {
            try {
              const base64 = await fileToBase64(file.originalFile);
              await saveScanSession(result.id, result, file, base64);
            } catch (err) {
              console.error('Failed to save session to IndexedDB', err);
            }
          }
        }

        // Show pipeline status for ~2.5s, then navigate
        await new Promise(r => setTimeout(r, 2500));
        router.push(`/results/${result.id}`);
      } catch (err: any) {
        console.error('Scan error:', err);
        didCompleteRef.current = true;
        setScanStatus('error');
        setError(err.message || 'An unknown error occurred');
      }
    }

    runScan();
  }, [file, scanId, router, setResult, setScanStatus, setError, addRecentScan]);

  useEffect(() => {
    if (!file) {
      router.push('/');
    }
  }, [file, router]);

  if (!file) {
    return null;
  }

  return (
    <div className="min-h-[calc(100vh-64px)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <motion.div
            animate={{ rotate: scanComplete ? 0 : scanStatus === 'error' ? 0 : 360 }}
            transition={{ duration: 2, repeat: (scanComplete || scanStatus === 'error') ? 0 : Infinity, ease: 'linear' }}
            className={`inline-flex items-center justify-center w-14 h-14 rounded-2xl border mb-5 ${
              scanStatus === 'error' 
                ? 'bg-danger/10 border-danger/20' 
                : 'bg-primary/8 border-primary/15'
            }`}
          >
            {scanStatus === 'error' ? (
              <AlertCircle size={26} className="text-danger" />
            ) : (
              <Shield size={26} className="text-primary" />
            )}
          </motion.div>

          <h1 className="text-2xl font-700 text-primary-text mb-2">
            {scanStatus === 'error' 
              ? 'Analysis failed' 
              : scanComplete 
                ? 'Analysis complete' 
                : 'Analyzing your image'}
          </h1>
          <p className={`text-sm ${scanStatus === 'error' ? 'text-danger' : 'text-secondary-text'}`}>
            {scanStatus === 'error'
              ? error || 'An unknown error occurred during scanning.'
              : scanComplete
              ? 'Navigating to your results...'
              : (() => {
                  const totalMs = SCAN_STAGES.reduce((s, st) => s + st.duration, 0);
                  const remaining = Math.max(0, Math.round((totalMs - elapsedMs) / 1000));
                  return `Deep scanning for privacy risks · ${remaining}s remaining`;
                })()
            }
          </p>
          
          {scanStatus === 'error' && (
            <button
              onClick={() => {
                setScanStatus('idle');
                setError(null);
                router.push('/');
              }}
              className="mt-6 px-4 py-2 bg-primary text-background rounded-lg text-sm font-medium min-h-[44px] min-w-[44px]"
            >
              Go back and try again
            </button>
          )}
        </motion.div>

        {/* Stage list */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-surface rounded-2xl border border-border shadow-soft overflow-hidden"
        >
          {/* Overall progress bar */}
          <div className="h-1 bg-brand-border">
            <motion.div
              className="h-full"
              style={{
                background: 'linear-gradient(90deg, #174C3C, #1E6B54)',
                width: `${overallProgress}%`,
                transition: 'width 0.3s linear',
              }}
            />
          </div>

          {/* Stages */}
          <div className="p-5 space-y-2">
            {stages.map((stage, i) => (
              <ScanStage
                key={stage.id}
                label={stage.label}
                status={stage.status}
                progress={stage.progress}
                duration={stage.duration}
                index={i}
              />
            ))}
          </div>

          {/* Detector summary (shown after scan completes) */}
          {scanComplete && pipelineStatusState && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              transition={{ type: "spring", stiffness: 150, damping: 20 }}
              className="border-t border-border"
            >
              <div className="px-5 py-4">
                <p className="text-xs font-600 text-muted-text uppercase tracking-wider mb-3">
                  Deep Research Detectors
                </p>
                <div className="space-y-1.5">
                  {([
                    { key: 'face',               label: 'Face Detection (InsightFace)',   icon: '👤' },
                    { key: 'ocr',                label: 'Text / OCR + PII Regex',        icon: '📄' },
                    { key: 'qr',                 label: 'QR / Barcode Scanner',          icon: '▣' },
                    { key: 'documentClassifier', label: 'Document Classification',       icon: '🏷️' },
                  ] as const).map(({ key, label, icon }) => {
                    const s = pipelineStatusState[key];
                    return (
                      <motion.div
                        key={key}
                        initial={{ opacity: 0, x: -6 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="flex items-center gap-2.5 text-xs"
                      >
                        <span>{icon}</span>
                        {s === 'success' ? (
                          <CheckCircle size={13} className="text-primary flex-shrink-0" />
                        ) : s === 'failed' ? (
                          <AlertCircle size={13} className="text-danger flex-shrink-0" />
                        ) : (
                          <div className="w-3.5 h-3.5 rounded-full border-2 border-border flex-shrink-0" />
                        )}
                        <span className={`flex-1 ${
                          s === 'failed' ? 'text-danger' :
                          s === 'skipped' ? 'text-muted-text' :
                          'text-primary-text'
                        }`}>
                          {label}
                        </span>
                        <span className={`font-600 text-2xs uppercase tracking-wide ${
                          s === 'success' ? 'text-primary' :
                          s === 'failed'  ? 'text-danger' :
                          'text-muted-text'
                        }`}>
                          {s === 'success' ? '✓ Done' :
                           s === 'failed'  ? '✗ Failed' :
                           '– Skipped'}
                        </span>
                      </motion.div>
                    );
                  })}
                  {/* Static rows for Python-side dedicated models */}
                  {(['🔞 NudeNet · Private body parts', '🔫 YOLOv8-Weapons · Guns & rifles', '🚬 YOLOv8-Smoking · Cigarettes & vapes', '🚗 YOLOv8-Plates · License plates', '🍺 YOLOv8-Safety · Alcohol & knives'] as string[]).map((row) => (
                    <motion.div
                      key={row}
                      initial={{ opacity: 0, x: -6 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="flex items-center gap-2.5 text-xs"
                    >
                      <CheckCircle size={13} className="text-primary flex-shrink-0" />
                      <span className="flex-1 text-primary-text">{row}</span>
                      <span className="font-600 text-2xs uppercase tracking-wide text-primary">✓ Done</span>
                    </motion.div>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </motion.div>

        {/* Privacy reassurance */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex justify-center gap-4 mt-6"
        >
          <span className="trust-pill text-2xs">
            <Lock size={10} className="text-primary/60" />
            Encrypted scan
          </span>
          <span className="trust-pill text-2xs">
            <Shield size={10} className="text-primary/60" />
            Never stored
          </span>
          <span className="trust-pill text-2xs">
            <Clock size={10} className="text-muted-text" />
            Auto-deleted after
          </span>
        </motion.div>
      </div>
    </div>
  );
}

function ScanStage({
  label,
  status,
  progress,
  duration,
  index,
}: {
  label: string;
  status: 'pending' | 'active' | 'done';
  progress: number;
  duration: number;
  index: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className={`rounded-xl transition-all duration-300 ${
        status === 'active'
          ? 'bg-primary/5 border border-primary/15 p-3.5'
          : status === 'done'
          ? 'p-3.5 opacity-70'
          : 'p-3.5 opacity-35'
      }`}
    >
      <div className="flex items-center gap-3">
        {/* Status icon */}
        <div className="flex-shrink-0 w-6 h-6">
          {status === 'done' && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: 'spring', stiffness: 500, damping: 25 }}
              className="w-6 h-6 rounded-full bg-primary flex items-center justify-center"
            >
              <CheckCircle size={13} className="text-background" />
            </motion.div>
          )}
          {status === 'active' && (
            <div className="w-6 h-6 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          )}
          {status === 'pending' && (
            <div className="w-6 h-6 rounded-full border-2 border-border" />
          )}
        </div>

        {/* Label + progress */}
        <div className="flex-1 min-w-0">
          <div className={`text-sm leading-tight ${
            status === 'done'
              ? 'text-secondary-text line-through decoration-brand-muted'
              : status === 'active'
              ? 'text-primary font-600'
              : 'text-muted-text'
          }`}>
            {status === 'done' ? `✓ ${label.replace('...', ' complete')}` : label}
          </div>

          {status === 'active' && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="stage-bar mt-1.5"
            >
              <div
                className="stage-bar-fill"
                style={{ 
                  width: `${progress}%`,
                  transition: `width ${duration}ms linear`
                }}
              />
            </motion.div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

