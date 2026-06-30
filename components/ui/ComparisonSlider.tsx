'use client';

import { useRef, useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight, Maximize } from 'lucide-react';
import { useAppStore } from '@/lib/store';
import Image from 'next/image';

interface ComparisonSliderProps {
  originalSrc: string;
  safeSrc: string;
  alt?: string;
  className?: string;
}

export function ComparisonSlider({
  originalSrc,
  safeSrc,
  alt = 'Privacy comparison',
  className = '',
}: ComparisonSliderProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [sliderPos, setSliderPos] = useState(50); // 0–100 (% from left)
  const [isDragging, setIsDragging] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const [imagesLoaded, setImagesLoaded] = useState({ original: false, safe: false });
  
  const isDevMode = useAppStore(state => state.isDevMode);
  const currentResult = useAppStore(state => state.currentResult);
  const currentFile = useAppStore(state => state.currentFile);

  const bothLoaded = imagesLoaded.original && imagesLoaded.safe;

  const updateSlider = useCallback((clientX: number) => {
    const container = containerRef.current;
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const x = clientX - rect.left;
    const pct = Math.max(5, Math.min(95, (x / rect.width) * 100));
    setSliderPos(pct);
  }, []);

  // Mouse events
  const onMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    updateSlider(e.clientX);
  };
  const onMouseMove = useCallback((e: MouseEvent) => {
    if (isDragging) updateSlider(e.clientX);
  }, [isDragging, updateSlider]);
  const onMouseUp = useCallback(() => setIsDragging(false), []);

  // Touch events
  const onTouchStart = (e: React.TouchEvent) => {
    setIsDragging(true);
    updateSlider(e.touches[0].clientX);
  };
  const onTouchMove = useCallback((e: TouchEvent) => {
    if (isDragging) updateSlider(e.touches[0].clientX);
  }, [isDragging, updateSlider]);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUp);
      window.addEventListener('touchmove', onTouchMove, { passive: true });
      window.addEventListener('touchend', onMouseUp);
    }
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      window.removeEventListener('touchmove', onTouchMove);
      window.removeEventListener('touchend', onMouseUp);
    };
  }, [isDragging, onMouseMove, onMouseUp, onTouchMove]);

  // Keyboard accessibility
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowLeft') setSliderPos(p => Math.max(5, p - 2));
    if (e.key === 'ArrowRight') setSliderPos(p => Math.min(95, p + 2));
    if (e.key === 'Home') setSliderPos(5);
    if (e.key === 'End') setSliderPos(95);
  };

  return (
    <div
      ref={containerRef}
      className={`comparison-slider select-none ${className}`}
      style={{
        minHeight: '300px',
        maxHeight: '600px',
        background: 'var(--surface-elevated)',
        cursor: isDragging ? 'ew-resize' : 'crosshair',
      }}
      onMouseDown={onMouseDown}
      onTouchStart={onTouchStart}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      role="slider"
      aria-label="Compare original and safe image. Use arrow keys to adjust."
      aria-valuemin={5}
      aria-valuemax={95}
      aria-valuenow={Math.round(sliderPos)}
      tabIndex={0}
      onKeyDown={onKeyDown}
    >
      {/* Skeleton while loading */}
      {!bothLoaded && (
        <div className="absolute inset-0 skeleton" />
      )}

      {/* ORIGINAL image (left side, full width, clipped by slider) */}
      <div className="absolute inset-0" style={{ clipPath: `inset(0 ${100 - sliderPos}% 0 0)` }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <div className="relative w-full h-full flex items-center justify-center">
          <img
            src={originalSrc}
            alt={`Original: ${alt}`}
            className="w-full h-full object-contain"
            onLoad={() => setImagesLoaded(p => ({ ...p, original: true }))}
            draggable={false}
          />
          
          {/* Debug Visualizer Overlay */}
          {isDevMode && currentResult && currentFile?.dimensions && imagesLoaded.original && (
            <div 
              className="absolute pointer-events-none"
              style={{
                aspectRatio: `${currentFile.dimensions.width} / ${currentFile.dimensions.height}`,
                width: currentFile.dimensions.width > currentFile.dimensions.height ? '100%' : 'auto',
                height: currentFile.dimensions.width > currentFile.dimensions.height ? 'auto' : '100%',
                maxHeight: '100%',
                maxWidth: '100%',
              }}
            >
              {currentResult.ocrWords?.map((word: any, i: number) => word.bbox ? (
                <div
                  key={`ocr-${i}`}
                  className="absolute border border-blue-500/50 bg-blue-500/10 flex items-center justify-center"
                  style={{
                    left: `${word.bbox.x}%`,
                    top: `${word.bbox.y}%`,
                    width: `${word.bbox.width}%`,
                    height: `${word.bbox.height}%`,
                  }}
                >
                  <span className="text-[8px] text-blue-500 bg-white/80 px-0.5 rounded truncate absolute -top-4 whitespace-nowrap opacity-50">{word.text}</span>
                </div>
              ) : null)}
              
              {currentResult.detections.map((det: any, i: number) => (
                <div
                  key={`det-${i}`}
                  className="absolute border-2 border-danger/70 bg-danger/10"
                  style={{
                    left: `${det.bbox.x}%`,
                    top: `${det.bbox.y}%`,
                    width: `${det.bbox.width}%`,
                    height: `${det.bbox.height}%`,
                  }}
                >
                  <span className="text-[10px] text-white font-bold bg-danger/80 px-1 rounded truncate absolute -top-5 whitespace-nowrap">
                    {det.type} ({Math.round(det.confidence || 0)}%)
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
        {/* ORIGINAL label */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: isHovered || isDragging ? 1 : 0.7 }}
          className="absolute top-3 left-3 trust-pill !bg-surface/90 backdrop-blur-sm text-xs font-600 text-primary-text shadow-sm"
        >
          Original
        </motion.div>
      </div>

      {/* SAFE image (right side, full width, clipped from left by slider) */}
      <div className="absolute inset-0" style={{ clipPath: `inset(0 0 0 ${sliderPos}%)` }}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={safeSrc}
          alt={`Safe version: ${alt}`}
          className="w-full h-full object-contain"
          style={{ filter: 'brightness(0.97)' }}
          onLoad={() => setImagesLoaded(p => ({ ...p, safe: true }))}
          draggable={false}
        />
        {/* SAFE label */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: isHovered || isDragging ? 1 : 0.7 }}
          className="absolute top-3 right-3 trust-pill !bg-primary/90 !text-background !border-primary/30 backdrop-blur-sm text-xs font-600 shadow-sm"
        >
          Safe Version
        </motion.div>
      </div>

      {/* Divider line */}
      <div
        className="comparison-handle"
        style={{ left: `calc(${sliderPos}% - 1px)` }}
      >
        {/* Handle knob */}
        <div
          className="comparison-handle-knob"
          style={{ boxShadow: '0 2px 12px rgba(0,0,0,0.18), 0 0 0 2px rgba(23,76,60,0.15)' }}
        >
          <div className="flex items-center gap-0.5">
            <ChevronLeft size={11} className="text-primary -mr-0.5" />
            <ChevronRight size={11} className="text-primary -ml-0.5" />
          </div>
        </div>
      </div>

      {/* Gradient overlay on edges */}
      <div className="absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-black/5 to-transparent pointer-events-none" />
      <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-black/5 to-transparent pointer-events-none" />
    </div>
  );
}

