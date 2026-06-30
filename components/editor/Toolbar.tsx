'use client';
import { useEditorStore, ToolType, BlurType } from '@/lib/editor-store';
import {
  MousePointer2, Square, Circle, Paintbrush, Undo, Redo,
  ZoomIn, ZoomOut, Maximize2, EyeOff, Grid3X3, Box,
  Minus, Expand, Slash, ChevronDown
} from 'lucide-react';
import { useState, useRef, useEffect } from 'react';

// ─── Blur type definitions ─────────────────────────────────────────────────
const BLUR_TYPES: { value: BlurType; label: string; icon: React.ReactNode; desc: string }[] = [
  {
    value: 'gaussian',
    label: 'Gaussian',
    desc: 'Smooth soft blur',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <circle cx="8" cy="8" r="6" fill="currentColor" opacity="0.15"/>
        <circle cx="8" cy="8" r="4" fill="currentColor" opacity="0.25"/>
        <circle cx="8" cy="8" r="2" fill="currentColor" opacity="0.5"/>
      </svg>
    ),
  },
  {
    value: 'pixelate',
    label: 'Pixelate',
    desc: 'Mosaic / pixel blocks',
    icon: <Grid3X3 size={16} />,
  },
  {
    value: 'black',
    label: 'Black Box',
    desc: 'Solid black fill',
    icon: <Box size={16} />,
  },
  {
    value: 'white',
    label: 'White Box',
    desc: 'Solid white fill',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <rect x="2" y="2" width="12" height="12" rx="2" stroke="currentColor" strokeWidth="1.5" fill="white"/>
      </svg>
    ),
  },
  {
    value: 'color',
    label: 'Color Block',
    desc: 'Custom solid color',
    icon: (
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
        <rect x="2" y="2" width="12" height="12" rx="2" fill="currentColor" opacity="0.6"/>
        <path d="M5 8 L8 5 L11 8 L8 11 Z" fill="white"/>
      </svg>
    ),
  },
  {
    value: 'motion',
    label: 'Motion',
    desc: 'Directional blur',
    icon: <Slash size={16} />,
  },
];

// ─── Shape / tool definitions ──────────────────────────────────────────────
const SHAPE_TOOLS: { id: ToolType; icon: React.ReactNode; label: string; shortcut: string }[] = [
  { id: 'select',           icon: <MousePointer2 size={17} />, label: 'Select',       shortcut: 'V' },
  { id: 'rectangle',        icon: <Square size={17} />,         label: 'Rectangle',    shortcut: 'R' },
  { id: 'rounded-rectangle',icon: (
    <svg width="17" height="17" viewBox="0 0 17 17" fill="none">
      <rect x="2" y="2" width="13" height="13" rx="4" stroke="currentColor" strokeWidth="1.8"/>
    </svg>
  ), label: 'Rounded Rect', shortcut: 'U' },
  { id: 'circle',           icon: <Circle size={17} />,         label: 'Circle',       shortcut: 'C' },
  { id: 'brush',            icon: <Paintbrush size={17} />,     label: 'Free Brush',   shortcut: 'B' },
];

// ─── Mini slider component ─────────────────────────────────────────────────
function MiniSlider({
  label, value, min, max, onChange, unit = '%', color = '#10B981'
}: {
  label: string; value: number; min: number; max: number;
  onChange: (v: number) => void; unit?: string; color?: string;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <span className="text-[10px] font-600 text-muted-text uppercase tracking-wide">{label}</span>
        <span className="text-[11px] font-700 text-primary-text tabular-nums">{value}{unit}</span>
      </div>
      <div className="relative h-5 flex items-center">
        <div className="absolute inset-y-0 flex items-center w-full">
          <div
            className="h-1 rounded-full"
            style={{
              width: `${((value - min) / (max - min)) * 100}%`,
              backgroundColor: color,
              minWidth: 4,
            }}
          />
          <div className="flex-1 h-1 rounded-full bg-border" />
        </div>
        <input
          type="range" min={min} max={max} value={value}
          onChange={e => onChange(Number(e.target.value))}
          className="absolute inset-0 w-full opacity-0 cursor-pointer h-full"
        />
      </div>
    </div>
  );
}

// ─── Main Toolbar ──────────────────────────────────────────────────────────
export function Toolbar() {
  const {
    currentTool, setTool,
    zoom, setZoom,
    undo, redo,
    defaultBlurType, defaultBlurStrength, defaultBrushSize, defaultColor,
    setDefaultBlur,
    selectedLayerIds, layers, updateLayer, commitLayerUpdate,
  } = useEditorStore();

  const [blurMenuOpen, setBlurMenuOpen] = useState(false);
  const blurMenuRef = useRef<HTMLDivElement>(null);

  // Active selected layer
  const activeLayer = layers.find(l => selectedLayerIds.includes(l.id));

  // Close blur menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (blurMenuRef.current && !blurMenuRef.current.contains(e.target as Node)) {
        setBlurMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Derived: effective blur settings (selected layer overrides defaults)
  const effectiveBlurType     = activeLayer?.blurType     ?? defaultBlurType;
  const effectiveBlurStrength = activeLayer?.blurStrength  ?? defaultBlurStrength;
  const effectiveBrushSize    = activeLayer?.brushSize     ?? defaultBrushSize;
  const effectiveColor        = activeLayer?.color         ?? defaultColor;

  const currentBlurDef = BLUR_TYPES.find(b => b.value === effectiveBlurType) ?? BLUR_TYPES[0];

  // Update both the active layer AND the global default when slider changes
  const handleBlurStrengthChange = (v: number) => {
    setDefaultBlur({ blurStrength: v });
    if (activeLayer) updateLayer(activeLayer.id, { blurStrength: v });
  };
  const handleBrushSizeChange = (v: number) => {
    setDefaultBlur({ brushSize: v });
    if (activeLayer) updateLayer(activeLayer.id, { brushSize: v });
  };
  const handleBlurTypeChange = (t: BlurType) => {
    setDefaultBlur({ blurType: t });
    if (activeLayer) {
      const prev = activeLayer.blurType;
      updateLayer(activeLayer.id, { blurType: t });
      commitLayerUpdate(activeLayer.id, { blurType: prev }, { blurType: t });
    }
    setBlurMenuOpen(false);
  };
  const handleColorChange = (c: string) => {
    setDefaultBlur({ color: c });
    if (activeLayer) updateLayer(activeLayer.id, { color: c });
  };

  return (
    /* ── Vertical sidebar on desktop, horizontal strip on mobile ── */
    <div className="
      order-last md:order-first
      w-full md:w-[200px]
      h-auto md:h-full
      bg-surface border-t md:border-t-0 md:border-r border-border
      flex flex-row md:flex-col
      items-center md:items-stretch
      gap-0
      z-10 shadow-sm relative
      overflow-x-auto md:overflow-y-auto md:overflow-x-hidden
      shrink-0
      select-none
    ">

      {/* ── Shape Tools Section ───────────────────────────────── */}
      <div className="flex flex-row md:flex-col items-center md:items-stretch gap-1 p-2 md:py-3 md:px-2 shrink-0">
        <p className="hidden md:block text-[9px] font-700 uppercase tracking-widest text-muted-text px-2 mb-1">Tools</p>

        {SHAPE_TOOLS.map(t => (
          <button
            key={t.id}
            onClick={() => setTool(t.id)}
            title={`${t.label} (${t.shortcut})`}
            className={`
              group relative shrink-0
              min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0
              md:w-full md:h-10
              rounded-xl flex items-center justify-center md:justify-start
              px-0 md:px-3 gap-2
              transition-all duration-150 border
              ${currentTool === t.id
                ? 'bg-primary/10 text-primary border-primary/30 shadow-sm'
                : 'text-muted-text hover:bg-[#F0F4F4] hover:text-primary-text border-transparent'
              }
            `}
          >
            {t.icon}
            <span className="hidden md:block text-xs font-500">{t.label}</span>

            {/* Shortcut badge on mobile */}
            <span className="
              md:hidden absolute -top-1 -right-1
              text-[8px] font-700 bg-surface-elevated border border-border
              rounded px-0.5 leading-tight opacity-0 group-hover:opacity-100
              transition-opacity pointer-events-none
            ">{t.shortcut}</span>
          </button>
        ))}
      </div>

      {/* ── Divider ───────────────────────────────────────────── */}
      <div className="w-px md:w-auto h-8 md:h-px md:mx-2 bg-border shrink-0 self-center md:self-auto my-0 md:my-1" />

      {/* ── Blur Controls Section ─────────────────────────────── */}
      <div className="flex flex-row md:flex-col items-center md:items-stretch gap-2 p-2 md:py-3 md:px-2 shrink-0 min-w-0">
        <p className="hidden md:block text-[9px] font-700 uppercase tracking-widest text-muted-text px-2 mb-1">Blur Style</p>

        {/* Blur type picker button */}
        <div ref={blurMenuRef} className="relative w-full shrink-0">
          <button
            onClick={() => setBlurMenuOpen(v => !v)}
            className="
              w-full min-w-[44px] min-h-[44px] md:min-h-0 md:h-9
              flex items-center justify-center md:justify-between
              gap-2 px-2 md:px-3
              rounded-xl border border-border
              bg-surface-elevated hover:bg-[#F0F4F4]
              text-primary-text transition-colors
            "
            title="Blur Type"
          >
            <span className="flex items-center gap-1.5 text-primary shrink-0">
              {currentBlurDef.icon}
              <span className="hidden md:block text-xs font-600 truncate">{currentBlurDef.label}</span>
            </span>
            <ChevronDown size={12} className="hidden md:block text-muted-text shrink-0" />
          </button>

          {/* Dropdown */}
          {blurMenuOpen && (
            <div className="
              absolute bottom-full md:bottom-auto md:top-full left-0 mb-1 md:mb-0 md:mt-1 z-50
              w-52 bg-surface rounded-2xl border border-border shadow-xl p-1
              animate-in fade-in slide-in-from-bottom-2 md:slide-in-from-top-2 duration-150
            ">
              {BLUR_TYPES.map(b => (
                <button
                  key={b.value}
                  onClick={() => handleBlurTypeChange(b.value)}
                  className={`
                    w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors text-left
                    ${effectiveBlurType === b.value
                      ? 'bg-primary/10 text-primary'
                      : 'hover:bg-[#F0F4F4] text-primary-text'
                    }
                  `}
                >
                  <span className="shrink-0">{b.icon}</span>
                  <span>
                    <div className="text-xs font-600">{b.label}</div>
                    <div className="text-[10px] text-muted-text">{b.desc}</div>
                  </span>
                  {effectiveBlurType === b.value && (
                    <span className="ml-auto text-primary">
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                        <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                      </svg>
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Blur strength slider — only show in desktop sidebar */}
        <div className="hidden md:block w-full px-1 space-y-4 mt-1">
          <MiniSlider
            label="Strength"
            value={effectiveBlurStrength}
            min={0}
            max={100}
            onChange={handleBlurStrengthChange}
            color="#3B82F6"
          />

          {(currentTool === 'brush' || activeLayer?.type === 'brush') && (
            <MiniSlider
              label="Brush Size"
              value={effectiveBrushSize}
              min={5}
              max={120}
              onChange={handleBrushSizeChange}
              unit="px"
              color="#8B5CF6"
            />
          )}

          {/* Color picker (for color blur type) */}
          {effectiveBlurType === 'color' && (
            <div className="space-y-1.5">
              <span className="text-[10px] font-600 text-muted-text uppercase tracking-wide block">Color</span>
              <input
                type="color"
                value={effectiveColor}
                onChange={e => handleColorChange(e.target.value)}
                className="w-full h-8 rounded-lg cursor-pointer border border-border"
              />
            </div>
          )}
        </div>
      </div>

      {/* ── Divider ───────────────────────────────────────────── */}
      <div className="w-px md:w-auto h-8 md:h-px md:mx-2 bg-border shrink-0 self-center md:self-auto my-0 md:my-1" />

      {/* ── History & View Controls ───────────────────────────── */}
      <div className="flex flex-row md:flex-col items-center md:items-stretch gap-1 p-2 md:py-3 md:px-2 shrink-0">
        <p className="hidden md:block text-[9px] font-700 uppercase tracking-widest text-muted-text px-2 mb-1">History</p>

        <button
          onClick={undo}
          className="shrink-0 min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 md:w-full md:h-10 rounded-xl flex items-center justify-center md:justify-start px-0 md:px-3 gap-2 text-muted-text hover:bg-[#F0F4F4] hover:text-primary-text border border-transparent transition-all"
          title="Undo (Ctrl+Z)"
        >
          <Undo size={17} />
          <span className="hidden md:block text-xs font-500">Undo</span>
        </button>

        <button
          onClick={redo}
          className="shrink-0 min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 md:w-full md:h-10 rounded-xl flex items-center justify-center md:justify-start px-0 md:px-3 gap-2 text-muted-text hover:bg-[#F0F4F4] hover:text-primary-text border border-transparent transition-all"
          title="Redo (Ctrl+Y)"
        >
          <Redo size={17} />
          <span className="hidden md:block text-xs font-500">Redo</span>
        </button>

        <div className="w-px md:w-auto h-6 md:h-px md:mx-2 bg-border shrink-0 self-center md:self-auto my-0 md:my-1" />

        <button
          onClick={() => setZoom(Math.min(zoom + 0.25, 4))}
          className="shrink-0 min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 md:w-full md:h-10 rounded-xl flex items-center justify-center md:justify-start px-0 md:px-3 gap-2 text-muted-text hover:bg-[#F0F4F4] hover:text-primary-text border border-transparent transition-all"
          title="Zoom In"
        >
          <ZoomIn size={17} />
          <span className="hidden md:block text-xs font-500">Zoom In</span>
        </button>

        <button
          onClick={() => setZoom(Math.max(zoom - 0.25, 0.1))}
          className="shrink-0 min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 md:w-full md:h-10 rounded-xl flex items-center justify-center md:justify-start px-0 md:px-3 gap-2 text-muted-text hover:bg-[#F0F4F4] hover:text-primary-text border border-transparent transition-all"
          title="Zoom Out"
        >
          <ZoomOut size={17} />
          <span className="hidden md:block text-xs font-500">Zoom Out</span>
        </button>

        <button
          onClick={() => { setZoom(1); }}
          className="shrink-0 min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 md:w-full md:h-10 rounded-xl flex items-center justify-center md:justify-start px-0 md:px-3 gap-2 text-muted-text hover:bg-[#F0F4F4] hover:text-primary-text border border-transparent transition-all"
          title="Reset Zoom"
        >
          <Maximize2 size={17} />
          <span className="hidden md:block text-xs font-600 tabular-nums text-muted-text">
            {Math.round(zoom * 100)}%
          </span>
        </button>
      </div>
    </div>
  );
}
