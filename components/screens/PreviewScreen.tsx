'use client';

import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ZoomIn, ZoomOut, RotateCw, Crop, RefreshCw,
  FileText, Image as ImageIcon, Monitor, FileCheck,
  ArrowLeft, Shield
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { formatFileSize } from '@/lib/utils';

const getFileTypeIcon = (type: string) => {
  if (type.startsWith('image/')) return ImageIcon;
  if (type === 'application/pdf') return FileText;
  return FileCheck;
};

interface PreviewScreenProps {
  scanId: string;
}

export function PreviewScreen({ scanId }: PreviewScreenProps) {
  const router = useRouter();
  const { currentFile, setScanStatus } = useAppStore();
  const [zoom, setZoom] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);

  const file = currentFile;

  useEffect(() => {
    if (!file) {
      router.push('/');
    }
  }, [file, router]);

  if (!file) {
    return null;
  }

  const handleDetectRisks = async () => {
    setIsLoading(true);
    setScanStatus('scanning');
    // Navigate to scanning page — scanning begins there
    router.push(`/scanning/${file.id}`);
  };

  const getIcon = () => getFileTypeIcon(file.type);

  const infoRows = [
    { label: 'Filename', value: file.name },
    { label: 'Size', value: formatFileSize(file.size) },
    {
      label: 'Dimensions',
      value: file.dimensions.width
        ? `${file.dimensions.width} × ${file.dimensions.height}px`
        : 'N/A',
    },
    {
      label: 'Type',
      value: file.type.split('/')[1]?.toUpperCase() || file.type,
    },
    {
      label: 'Uploaded',
      value: new Date(file.uploadedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ];

  return (
    <div className="min-h-[calc(100vh-64px)] flex flex-col px-4 py-8">
      <div className="max-w-7xl mx-auto w-full flex-1">
        {/* Back button */}
        <motion.button
          initial={{ opacity: 0, x: -10 }}
          animate={{ opacity: 1, x: 0 }}
          onClick={() => router.push('/')}
          id="preview-back"
          className="flex items-center gap-1.5 text-sm text-secondary-text hover:text-primary-text transition-colors mb-6 min-h-[44px] min-w-[44px]"
        >
          <ArrowLeft size={15} />
          Upload another file
        </motion.button>

        {/* Main layout */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 h-full">
          {/* === LEFT: Image Preview === */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="flex flex-col"
          >
            {/* Toolbar */}
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-600 text-primary-text">Preview</h2>
              <div className="flex items-center gap-1.5">
                <ToolButton
                  icon={ZoomOut}
                  label="Zoom out"
                  onClick={() => setZoom(z => Math.max(0.3, z - 0.2))}
                  disabled={zoom <= 0.3}
                />
                <span className="text-xs font-600 text-secondary-text w-12 text-center tabular-nums">
                  {Math.round(zoom * 100)}%
                </span>
                <ToolButton
                  icon={ZoomIn}
                  label="Zoom in"
                  onClick={() => setZoom(z => Math.min(3, z + 0.2))}
                  disabled={zoom >= 3}
                />
                <div className="w-px h-4 bg-brand-border mx-1" />
                <ToolButton
                  icon={RotateCw}
                  label="Rotate"
                  onClick={() => setRotation(r => (r + 90) % 360)}
                />
                <ToolButton icon={Crop} label="Crop" onClick={() => {}} />
              </div>
            </div>

            {/* Image canvas */}
            <div className="flex-1 bg-surface rounded-2xl border border-border overflow-hidden relative flex items-center justify-center"
              style={{ minHeight: '420px', boxShadow: '0 4px 24px rgba(23,76,60,0.06)' }}
            >
              {/* Grid background */}
              <div className="absolute inset-0 opacity-30"
                style={{
                  backgroundImage: 'linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)',
                  backgroundSize: '20px 20px',
                }}
              />

              {file.type.startsWith('image/') ? (
                <motion.img
                  ref={imgRef}
                  src={file.previewUrl}
                  alt={`Preview of ${file.name}`}
                  className="relative z-10 max-w-full max-h-full object-contain"
                  style={{
                    transform: `scale(${zoom}) rotate(${rotation}deg)`,
                    transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    maxHeight: '500px',
                  }}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                />
              ) : (
                <div className="relative z-10 flex flex-col items-center gap-4 text-secondary-text">
                  <FileText size={64} className="text-brand-border" />
                  <div className="text-center">
                    <div className="text-sm font-600 text-primary-text">{file.name}</div>
                    <div className="text-xs text-secondary-text mt-1">PDF preview available after scan</div>
                  </div>
                </div>
              )}
            </div>

            {/* Zoom reset */}
            {zoom !== 1 && (
              <button
                onClick={() => { setZoom(1); setRotation(0); }}
                className="mt-2 text-xs text-secondary-text hover:text-primary transition-colors self-center min-h-[44px] min-w-[44px]"
              >
                Reset view
              </button>
            )}
          </motion.div>

          {/* === RIGHT: Info + Actions === */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="flex flex-col gap-4"
          >
            {/* File info card */}
            <div className="bg-surface rounded-2xl border border-border p-5 w-full md:w-auto"
              style={{ boxShadow: '0 4px 24px rgba(23,76,60,0.06)' }}
            >
              <div className="flex items-center gap-3 mb-5">
                <div className="w-10 h-10 rounded-xl bg-primary/8 flex items-center justify-center">
                  {React.createElement(getIcon(), { size: 20, className: "text-primary" })}
                </div>
                <div>
                  <div className="text-sm font-700 text-primary-text truncate max-w-[200px]">
                    {file.name}
                  </div>
                  <div className="text-xs text-secondary-text">Ready to analyze</div>
                </div>
              </div>

              <div className="space-y-3">
                {infoRows.map(({ label, value }) => (
                  <div key={label} className="flex justify-between items-center py-2 border-b border-border/60 last:border-0">
                    <span className="text-xs text-secondary-text font-500">{label}</span>
                    <span className="text-xs font-600 text-primary-text text-right max-w-[160px] truncate font-mono">
                      {value}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* AI preview */}
            <div className="bg-primary/4 border border-primary/15 rounded-2xl p-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-primary/12 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Shield size={15} className="text-primary" />
                </div>
                <div>
                  <div className="text-sm font-600 text-primary mb-1">What we&apos;ll check</div>
                  <div className="text-xs text-secondary-text space-y-1 leading-relaxed">
                    {[
                      'Phone numbers & emails',
                      'Aadhaar, PAN, Bank details',
                      'Faces & QR codes',
                      'Addresses & passwords',
                    ].map(item => (
                      <div key={item} className="flex items-center gap-1.5">
                        <div className="w-1 h-1 rounded-full bg-brand-accent flex-shrink-0" />
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="space-y-3 w-full md:w-auto">
              <button
                onClick={() => {
                  setIsLoading(true);
                  setScanStatus('scanning');
                  router.push(`/scanning/${file.id}`);
                }}
                disabled={isLoading}
                id="detect-btn"
                className="w-full flex items-center justify-center gap-2.5 bg-primary hover:bg-primary/90 text-background font-700 text-base px-5 py-4 min-h-[44px] rounded-2xl transition-all duration-200 shadow-md hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <Shield size={18} />
                {isLoading ? 'Preparing...' : 'Detect'}
              </button>

              <button
                id="replace-file-btn"
                onClick={() => router.push('/')}
                className="w-full flex items-center justify-center gap-2 text-secondary-text hover:text-primary-text font-500 text-sm px-5 py-2 min-h-[44px] min-w-[44px] transition-all duration-200"
              >
                <RefreshCw size={14} />
                Replace File
              </button>
            </div>

            {/* Privacy notice */}
            <div className="text-center text-xs text-muted-text leading-relaxed">
              <Monitor size={11} className="inline mr-1" />
              Files are encrypted and automatically deleted after processing.
              We never store your original images.
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

function ToolButton({
  icon: Icon,
  label,
  onClick,
  disabled = false,
}: {
  icon: React.ElementType;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      aria-label={label}
      onClick={onClick}
      disabled={disabled}
      className="w-11 h-11 rounded-lg flex items-center justify-center text-secondary-text hover:text-primary-text hover:bg-brand-border/50 transition-all duration-150 disabled:opacity-30 disabled:cursor-not-allowed"
    >
      <Icon size={15} />
    </button>
  );
}

