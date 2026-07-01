'use client';

import { useCallback, useState, useRef, useMemo, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload, Image, FileText, Shield, Lock, Clock,
  AlertCircle, Zap, ChevronRight, Eye, History,
  ShieldCheck, Search, Star, RotateCw
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { getImageDimensions, formatFileSize, uuid, formatTimeAgo } from '@/lib/utils';
import { RiskBadge } from '@/components/ui/PrivacyComponents';

const ACCEPTED_TYPES = {
  'image/*': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.heic', '.avif'],
  'application/pdf': ['.pdf'],
};

const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

export function UploadScreen({ setScanId }: { setScanId?: (id: string) => void }) {
  const router = useRouter();
  const { setFile, recentScans, setScanStatus, setCurrentStage } = useAppStore();
  const [error, setError] = useState<string | null>(null);
  const [isDragActive, setIsDragActive] = useState(false);
  const [resumableJobId, setResumableJobId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const jobId = localStorage.getItem('lastJobId');
    if (jobId) {
      setResumableJobId(jobId);
    }
  }, []);

  const handleResume = () => {
    if (!resumableJobId) return;
    const dummyFile = {
      id: resumableJobId,
      name: 'Resumed Scan',
      size: 0,
      dimensions: { width: 0, height: 0 },
      type: 'image/jpeg',
      previewUrl: '',
      uploadedAt: new Date(),
    };
    setFile(dummyFile as any);
    router.push(`/scan/${resumableJobId}`);
  };

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);

      // Validate size
      if (file.size > MAX_SIZE) {
        setError(`File too large. Maximum size is 10 MB (got ${formatFileSize(file.size)})`);
        return;
      }

      // Build preview URL
      const previewUrl = URL.createObjectURL(file);

      // Get dimensions (for images)
      let dimensions = { width: 0, height: 0 };
      if (file.type.startsWith('image/')) {
        try {
          dimensions = await getImageDimensions(file);
        } catch {}
      }

      const scanFile = {
        id: uuid(),
        name: file.name,
        size: file.size,
        dimensions,
        type: file.type,
        previewUrl,
        uploadedAt: new Date(),
        originalFile: file,
      };

      setFile(scanFile);
      router.push(`/preview/${scanFile.id}`);
    },
    [router, setFile]
  );

  const { getRootProps, getInputProps, isDragReject } = useDropzone({
    accept: ACCEPTED_TYPES,
    maxSize: MAX_SIZE,
    multiple: false,
    onDrop: (accepted, rejected) => {
      setIsDragActive(false);
      if (rejected.length > 0) {
        const err = rejected[0].errors[0];
        setError(err.code === 'file-too-large'
          ? `File too large. Max 10 MB.`
          : err.code === 'file-invalid-type'
          ? 'Unsupported format. Use any Image format, or PDF.'
          : 'Invalid file.');
        return;
      }
      if (accepted.length > 0) handleFile(accepted[0]);
    },
    onDragEnter: () => setIsDragActive(true),
    onDragLeave: () => setIsDragActive(false),
  });

  return (
    <div className="min-h-[calc(100vh-64px)] flex flex-col items-center justify-center px-4 py-6 sm:py-12 overflow-hidden relative">
      {/* Background Protection Scrim for readability (Dark mode only) */}
      <div className="absolute inset-0 dark:bg-text-scrim -z-10 pointer-events-none transition-colors duration-700" />

      <div className="w-full max-w-2xl relative z-10 mt-8">
        
        {resumableJobId && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8 p-4 rounded-2xl glass-panel border border-primary/40 flex items-center justify-between shadow-soft bg-surface"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <RotateCw size={20} className="text-primary animate-spin" style={{ animationDuration: '3s' }} />
              </div>
              <div>
                <p className="text-sm font-600 text-primary-text">Scan in progress</p>
                <p className="text-xs text-secondary-text">You have an ongoing privacy scan.</p>
              </div>
            </div>
            <button
              onClick={handleResume}
              className="text-sm font-500 bg-primary text-background px-5 py-2.5 rounded-xl hover:bg-primary/90 transition-colors"
            >
              Resume
            </button>
          </motion.div>
        )}
        
        {/* Floating Marketing Badges (Desktop Only) */}
        <motion.div 
          initial={{ opacity: 0, x: -30 }} 
          animate={{ opacity: 1, x: 0 }} 
          transition={{ delay: 0.6, type: "spring" }}
          className="absolute -left-10 xl:-left-40 top-12 hidden lg:flex items-center gap-3 rounded-2xl p-4 w-56 z-20 glass-panel shadow-card"
        >
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10 text-primary shrink-0">
            <ShieldCheck size={20} />
          </div>
          <div>
            <p className="text-sm font-600 text-primary-text">95.23% Accuracy</p>
            <p className="text-xs text-secondary-text">Industry leading precision</p>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, x: -30 }} 
          animate={{ opacity: 1, x: 0 }} 
          transition={{ delay: 0.7, type: "spring" }}
          className="absolute -left-16 xl:-left-48 top-[40%] hidden lg:flex items-center gap-3 rounded-2xl p-4 w-56 z-20 glass-panel shadow-card"
        >
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10 text-primary shrink-0">
            <Search size={20} />
          </div>
          <div>
            <p className="text-sm font-600 text-primary-text">Detects Everything</p>
            <p className="text-xs text-secondary-text">Faces, PII, Cards & more</p>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, x: -30 }} 
          animate={{ opacity: 1, x: 0 }} 
          transition={{ delay: 0.8, type: "spring" }}
          className="absolute -left-10 xl:-left-40 bottom-24 hidden lg:flex items-center gap-3 rounded-2xl p-4 w-56 z-20 glass-panel shadow-card"
        >
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10 text-primary shrink-0">
            <Lock size={20} />
          </div>
          <div>
            <p className="text-sm font-600 text-primary-text">Military-Grade Safe</p>
            <p className="text-xs text-secondary-text">On-device encryption</p>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, x: 30 }} 
          animate={{ opacity: 1, x: 0 }} 
          transition={{ delay: 0.75, type: "spring" }}
          className="absolute -right-10 xl:-right-40 top-24 hidden lg:flex items-center gap-3 rounded-2xl p-4 w-56 z-20 glass-panel shadow-card"
        >
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-primary/10 text-primary shrink-0">
            <Zap size={20} />
          </div>
          <div>
            <p className="text-sm font-600 text-primary-text">Blazing Fast</p>
            <p className="text-xs text-secondary-text">Instant redaction</p>
          </div>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0, x: 30 }} 
          animate={{ opacity: 1, x: 0 }} 
          transition={{ delay: 0.85, type: "spring" }}
          className="absolute -right-16 xl:-right-48 bottom-32 hidden lg:flex items-center gap-3 rounded-2xl p-4 w-60 z-20 glass-panel shadow-card"
        >
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-accent/10 text-accent shrink-0">
            <Star size={20} />
          </div>
          <div>
            <p className="text-sm font-600 text-primary-text">Highly Affordable</p>
            <p className="text-xs text-secondary-text">Pro from $1 to $3 / mo</p>
          </div>
        </motion.div>


        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
          className="text-center mb-10 relative z-10"
        >
          <div className="inline-flex items-center gap-2 glass-panel text-primary rounded-full px-4 py-1.5 text-xs font-500 mb-6 shadow-soft min-h-[44px]">
            <Zap size={12} className="fill-primary" />
            <span>AI-Powered Privacy Protection</span>
          </div>
          <h1 className="font-serif font-400 text-primary-text dark:text-readable-shadow tracking-tight leading-tight mb-4 transition-all duration-300" style={{ fontSize: 'clamp(2.5rem, 8vw, 4.5rem)' }}>
            Protect what you
            <span className="text-primary italic"> share</span>
          </h1>
          <p className="text-secondary-text dark:text-readable-shadow text-base sm:text-lg max-w-md mx-auto leading-relaxed transition-all duration-300">
            Upload any image or document. Our AI detects exposed personal data and creates a safe redacted version instantly.
          </p>
        </motion.div>

        {/* Drop Zone */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 120, damping: 20, delay: 0.1 }}
          className="relative z-10"
        >
          <div
            {...getRootProps()}
            id="upload-drop-zone"
            className={`relative rounded-3xl p-6 sm:p-14 text-center cursor-pointer transition-all duration-500 group overflow-hidden glass-panel ${
              isDragActive
                ? 'border-primary ring-2 ring-primary/20 scale-[1.02] shadow-primary-glow'
                : isDragReject
                ? 'border-danger bg-danger/5'
                : 'hover:border-primary/50 hover:-translate-y-1 hover:shadow-card'
            }`}
          >
            {/* Animated Border Glow (visible on hover) */}
            <div className="absolute inset-0 z-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700 bg-gradient-to-r from-transparent via-primary/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] ease-in-out" />
            
            {/* Corner Highlights */}
            <div className="absolute top-0 left-0 w-8 h-8 border-t border-l border-primary/0 group-hover:border-primary/40 rounded-tl-3xl transition-colors duration-500" />
            <div className="absolute top-0 right-0 w-8 h-8 border-t border-r border-primary/0 group-hover:border-primary/40 rounded-tr-3xl transition-colors duration-500" />
            <div className="absolute bottom-0 left-0 w-8 h-8 border-b border-l border-primary/0 group-hover:border-primary/40 rounded-bl-3xl transition-colors duration-500" />
            <div className="absolute bottom-0 right-0 w-8 h-8 border-b border-r border-primary/0 group-hover:border-primary/40 rounded-br-3xl transition-colors duration-500" />

            {/* Light reflection gradient */}
            <div className="absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" style={{ background: 'radial-gradient(circle at 50% -20%, rgba(255,255,255,0.05), transparent 70%)' }} />

            {/* Dot pattern */}
            <div
              className="absolute inset-0 rounded-3xl opacity-20 pointer-events-none"
              style={{
                backgroundImage: 'radial-gradient(circle, var(--primary) 1px, transparent 1px)',
                backgroundSize: '24px 24px',
              }}
            />

            {/* Soft floating particles (CSS animation) */}
            <div className="absolute inset-0 overflow-hidden rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-1000 pointer-events-none z-0">
               {[
                 { left: 20, dur: 3.5, del: 0.5 },
                 { left: 55, dur: 2.8, del: 1.2 },
                 { left: 80, dur: 4.2, del: 0.2 },
                 { left: 12, dur: 3.1, del: 1.8 },
                 { left: 68, dur: 2.5, del: 0.9 },
                 { left: 40, dur: 4.8, del: 1.5 },
                 { left: 90, dur: 2.2, del: 0.1 },
                 { left: 33, dur: 3.9, del: 1.0 },
               ].map((p, i) => (
                 <motion.div
                   key={i}
                   className="absolute w-[2px] h-[2px] rounded-full bg-primary/40 shadow-[0_0_4px_rgba(23,76,60,0.5)]"
                   initial={{ y: 200, opacity: 0 }}
                   animate={{ y: -100, opacity: [0, 1, 0] }}
                   transition={{ duration: p.dur, repeat: Infinity, ease: "linear", delay: p.del }}
                   style={{ left: `${p.left}%` }}
                 />
               ))}
            </div>

            <input {...getInputProps()} id="upload-file-input" />

            {/* Upload Icon (Floating) */}
            <motion.div
              animate={isDragActive ? { scale: 1.15, y: -4 } : { scale: 1, y: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 20 }}
              className="relative z-10"
            >
              <motion.div 
                animate={{ y: [0, -6, 0] }}
                transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-surface border border-border mb-6 group-hover:bg-primary/5 group-hover:border-primary/30 shadow-soft group-hover:shadow-primary-glow transition-all duration-500 relative"
              >
                {/* Icon Inner Glow */}
                <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 shadow-[inset_0_0_12px_rgba(23,76,60,0.05)]" />
                
                <Upload
                  size={32}
                  className={`transition-colors duration-300 relative z-10 ${
                    isDragActive ? 'text-primary' : 'text-primary/70 group-hover:text-primary'
                  }`}
                />
              </motion.div>

              <h2 className="text-xl sm:text-2xl font-600 text-primary-text mb-2 dark:text-readable-shadow transition-all group-hover:text-primary">
                {isDragActive ? 'Drop to analyze' : 'Drop image here'}
              </h2>
              <p className="text-secondary-text text-sm mb-1 dark:text-readable-shadow transition-all">
                or{' '}
                <span className="text-primary font-500 underline underline-offset-4 group-hover:text-primary-light transition-colors">
                  browse files
                </span>
              </p>
              <p className="text-muted-text text-xs mt-4">
                Any Image or PDF &nbsp;•&nbsp; Max 10 MB
              </p>
            </motion.div>
          </div>

          {/* Error message */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mt-4 flex items-center gap-2 text-sm text-danger bg-danger/10 border border-danger/20 rounded-xl px-4 py-3 backdrop-blur-md"
              >
                <AlertCircle size={15} className="flex-shrink-0" />
                {error}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Privacy notice */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex flex-wrap justify-center gap-2 mt-6 relative z-10"
        >
          {[
            { icon: Lock, text: 'Encrypted in transit' },
            { icon: Clock, text: 'Deleted after processing' },
            { icon: Shield, text: 'GDPR compliant' },
          ].map(({ icon: Icon, text }) => (
            <span
              key={text}
              className="inline-flex items-center gap-1.5 text-xs text-secondary-text glass-panel rounded-full px-3 py-1.5 shadow-sm"
            >
              <Icon size={12} className="text-primary" />
              {text}
            </span>
          ))}
        </motion.div>

        {/* Format cards */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 120, damping: 20, delay: 0.35 }}
          className="grid grid-cols-3 gap-3 mt-10 relative z-10 w-full md:w-auto"
        >
          {[
            { icon: Image, label: 'All Images', desc: 'Photos, screenshots...', color: 'var(--primary)' },
            { icon: FileText, label: 'PDF', desc: 'Documents & forms', color: 'var(--warning)' },
            { icon: Eye, label: 'Example scan', desc: 'See how it works', color: 'var(--muted-text)', demo: true },
          ].map(({ icon: Icon, label, desc, color, demo }) => (
            <button
              key={label}
              type="button"
              id={`format-${label.toLowerCase().replace(/\W/g, '-')}`}
              onClick={(e) => { e.stopPropagation(); if (demo) router.push('/how-it-works'); }}
              className="group flex flex-col items-center gap-2 p-4 min-h-[44px] min-w-[44px] glass-panel hover:border-primary/40 hover:shadow-soft transition-all duration-300 text-center rounded-2xl hover:-translate-y-0.5 relative z-50"
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center bg-surface border border-border group-hover:border-transparent transition-colors"
                style={{ '--hover-bg': `color-mix(in srgb, ${color} 15%, transparent)` } as React.CSSProperties}
              >
                <Icon size={18} style={{ color }} className="opacity-80 group-hover:opacity-100 transition-opacity" />
              </div>
              <div>
                <div className="text-xs font-500 text-primary-text">{label}</div>
                <div className="text-[11px] text-secondary-text mt-0.5">{desc}</div>
              </div>
            </button>
          ))}
        </motion.div>

        {/* Recent scans */}
        {recentScans.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.45 }}
            className="mt-12 relative z-10"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-sm font-500 text-primary-text dark:text-readable-shadow">
                <History size={15} className="text-secondary-text" />
                Recent scans
              </div>
              <button className="text-xs text-secondary-text hover:text-primary transition-colors dark:text-readable-shadow">
                View all
              </button>
            </div>

            <div className="space-y-2">
              {recentScans.slice(0, 3).map((scan, i) => (
                <motion.div
                  key={scan.id}
                  onClick={() => router.push(`/results/${scan.id}`)}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + i * 0.07 }}
                  className="flex items-center gap-3 p-3 glass-panel hover:shadow-soft transition-all duration-200 cursor-pointer group rounded-xl hover:-translate-y-0.5"
                >
                  {/* File icon */}
                  <div className="w-10 h-10 rounded-lg bg-surface border border-border flex items-center justify-center flex-shrink-0 group-hover:border-primary/20 transition-colors">
                    <FileText size={16} className="text-secondary-text group-hover:text-primary transition-colors" />
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-500 text-primary-text truncate">{scan.filename}</div>
                    <div className="text-xs text-secondary-text mt-0.5">
                      {scan.detectionCount} items detected · {formatTimeAgo(scan.scannedAt)}
                    </div>
                  </div>

                  {/* Score + risk */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <div className="text-right">
                      <div className="text-sm font-600 text-primary-text">{scan.privacyScore}</div>
                      <div className="text-[10px] text-muted-text">score</div>
                    </div>
                    <RiskBadge riskLevel={scan.riskLevel} />
                  </div>

                  <ChevronRight size={16} className="text-muted-text group-hover:text-primary transition-colors flex-shrink-0 ml-1" />
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
