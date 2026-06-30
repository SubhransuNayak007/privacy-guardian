'use client';
import { useState, useRef } from 'react';
import { useEditorStore, EditorLayer, BlurType } from '@/lib/editor-store';
import {
  Eye, EyeOff, Lock, Unlock, Copy, Trash2, Layers,
  Settings2, Plus, Check, Grip, Paintbrush, Grid3X3,
  Box, Square, Circle, Minus, ChevronRight, Sliders
} from 'lucide-react';
import { useAppStore } from '@/lib/store';
import { PrivacyScoreRing } from '@/components/ui/PrivacyComponents';
import { DETECTION_CONFIG } from '@/types';

// ─── Blur type visual options ──────────────────────────────────────────────
const BLUR_TYPES: { value: BlurType; label: string; preview: React.ReactNode }[] = [
  {
    value: 'gaussian',
    label: 'Blur',
    preview: (
      <div className="w-full h-full rounded-md relative overflow-hidden bg-gradient-to-br from-gray-300 to-gray-500">
        <div className="absolute inset-0 backdrop-blur-sm bg-white/20 rounded-md" />
      </div>
    ),
  },
  {
    value: 'pixelate',
    label: 'Pixel',
    preview: (
      <div className="w-full h-full rounded-md grid grid-cols-3 grid-rows-3 gap-0.5 p-0.5 bg-gray-200">
        {Array.from({ length: 9 }).map((_, i) => (
          <div key={i} className="rounded-[2px]" style={{ background: `hsl(${i * 40}, 40%, 60%)` }} />
        ))}
      </div>
    ),
  },
  {
    value: 'black',
    label: 'Black',
    preview: <div className="w-full h-full rounded-md bg-black" />,
  },
  {
    value: 'white',
    label: 'White',
    preview: <div className="w-full h-full rounded-md bg-white border border-gray-200" />,
  },
  {
    value: 'color',
    label: 'Color',
    preview: <div className="w-full h-full rounded-md bg-gradient-to-br from-purple-400 to-pink-400" />,
  },
  {
    value: 'motion',
    label: 'Motion',
    preview: (
      <div className="w-full h-full rounded-md bg-gray-200 overflow-hidden relative">
        {[0, 1, 2, 3, 4].map(i => (
          <div key={i} className="absolute h-full bg-gray-400/60" style={{ left: `${i * 25}%`, width: 3, transform: `skewX(-15deg)` }} />
        ))}
      </div>
    ),
  },
];

// ─── Inline slider component ───────────────────────────────────────────────
function PanelSlider({
  label, value, min, max, onChange, onCommit, unit = '%', accent = '#3B82F6'
}: {
  label: string; value: number; min: number; max: number;
  onChange: (v: number) => void;
  onCommit?: (prev: number, next: number) => void;
  unit?: string; accent?: string;
}) {
  const startRef = useRef<number | null>(null);
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between items-center">
        <span className="text-[11px] font-600 text-secondary-text">{label}</span>
        <span
          className="text-[11px] font-700 tabular-nums px-1.5 py-0.5 rounded-md text-primary-text"
          style={{ background: `${accent}18` }}
        >
          {value}{unit}
        </span>
      </div>
      <div className="relative h-5 flex items-center group">
        {/* Track */}
        <div className="absolute w-full h-1.5 rounded-full bg-border overflow-hidden">
          <div className="h-full rounded-full transition-none" style={{ width: `${pct}%`, background: accent }} />
        </div>
        {/* Thumb (visual only) */}
        <div
          className="absolute w-4 h-4 rounded-full border-2 border-white shadow-md transition-none pointer-events-none"
          style={{ left: `calc(${pct}% - 8px)`, background: accent }}
        />
        {/* Native range (transparent overlay for interaction) */}
        <input
          type="range" min={min} max={max} value={value}
          onPointerDown={() => { startRef.current = value; }}
          onChange={e => onChange(Number(e.target.value))}
          onPointerUp={e => {
            if (startRef.current !== null && onCommit) {
              onCommit(startRef.current, Number(e.currentTarget.value));
            }
            startRef.current = null;
          }}
          className="absolute inset-0 w-full opacity-0 cursor-pointer h-full"
        />
      </div>
    </div>
  );
}

// ─── Main LayersPanel ──────────────────────────────────────────────────────
export function LayersPanel({ onClose }: { onClose?: () => void }) {
  const {
    layers, selectedLayerIds, setSelectedLayers,
    updateLayer, commitLayerUpdate,
    deleteLayers, duplicateLayers, addLayer,
    trustedFaceImages, setTrustedFaceImages,
    defaultBlurType, defaultBlurStrength, defaultBrushSize, defaultColor,
    setDefaultBlur,
  } = useEditorStore();

  const { currentResult, currentFile } = useAppStore();
  const [appliedSuggestions, setAppliedSuggestions] = useState<Set<string>>(new Set());
  const [propsOpen, setPropsOpen] = useState(true);

  const activeLayer = layers.find(l => selectedLayerIds.includes(l.id));
  const suggestions = currentResult?.detections.filter(d => !d.redacted) || [];

  // ── Layer blur type change
  const changeBlurType = (t: BlurType) => {
    if (!activeLayer) { setDefaultBlur({ blurType: t }); return; }
    const prev = activeLayer.blurType;
    updateLayer(activeLayer.id, { blurType: t });
    commitLayerUpdate(activeLayer.id, { blurType: prev }, { blurType: t });
  };

  const handleApplySuggestion = (detection: any) => {
    const imgW = currentFile?.dimensions?.width || 1000;
    const imgH = currentFile?.dimensions?.height || 1000;
    addLayer({
      type: 'rect',
      x: (detection.bbox.x / 100) * imgW,
      y: (detection.bbox.y / 100) * imgH,
      width: (detection.bbox.width / 100) * imgW,
      height: (detection.bbox.height / 100) * imgH,
      blurType: 'gaussian',
      blurStrength: 80,
      opacity: 1,
      visible: true,
      locked: false,
    });
    setAppliedSuggestions(prev => new Set(prev).add(detection.id));
  };

  // ── Effective values (layer overrides global defaults)
  const eff = {
    blurType:     activeLayer?.blurType     ?? defaultBlurType,
    blurStrength: activeLayer?.blurStrength  ?? defaultBlurStrength,
    brushSize:    activeLayer?.brushSize     ?? defaultBrushSize,
    color:        activeLayer?.color         ?? defaultColor,
    opacity:      activeLayer?.opacity       ?? 1,
  };

  const updateEff = <K extends keyof typeof eff>(key: K, val: any) => {
    if (activeLayer) {
      updateLayer(activeLayer.id, { [key]: val });
    } else {
      // Update global default when no layer selected
      if (key === 'blurType')     setDefaultBlur({ blurType: val });
      if (key === 'blurStrength') setDefaultBlur({ blurStrength: val });
      if (key === 'brushSize')    setDefaultBlur({ brushSize: val });
      if (key === 'color')        setDefaultBlur({ color: val });
    }
  };

  const commitEff = <K extends keyof typeof eff>(key: K, prev: any, next: any) => {
    if (key === 'blurType')     setDefaultBlur({ blurType: next });
    if (key === 'blurStrength') setDefaultBlur({ blurStrength: next });
    if (key === 'brushSize')    setDefaultBlur({ brushSize: next });
    if (key === 'color')        setDefaultBlur({ color: next });
    if (activeLayer) {
      commitLayerUpdate(activeLayer.id, { [key]: prev }, { [key]: next });
    }
  };

  return (
    <div className="w-full md:w-80 bg-surface border-l border-border flex flex-col h-full shadow-sm relative z-10 overflow-hidden">

      {/* ── Panel header ───────────────────────────────────────── */}
      <div className="h-12 flex items-center justify-between px-4 border-b border-border shrink-0 bg-surface">
        <div className="flex items-center gap-2">
          <Sliders size={14} className="text-muted-text" />
          <span className="text-sm font-700 text-primary-text">Edit Panel</span>
        </div>
        {onClose && (
          <button className="md:hidden p-1 text-muted-text hover:text-primary-text" onClick={onClose}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="14" y1="4" x2="4" y2="14"/><line x1="4" y1="4" x2="14" y2="14"/>
            </svg>
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">

        {/* ── Blur Style Section ─────────────────────────────────── */}
        <div className="p-4 border-b border-border space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-700 text-primary-text">Blur Style</span>
            {activeLayer ? (
              <span className="text-[10px] text-primary font-600 bg-primary/10 px-2 py-0.5 rounded-full">
                Editing Layer
              </span>
            ) : (
              <span className="text-[10px] text-muted-text font-500 bg-surface-elevated px-2 py-0.5 rounded-full">
                Default (new shapes)
              </span>
            )}
          </div>

          {/* Visual blur type grid */}
          <div className="grid grid-cols-3 gap-2">
            {BLUR_TYPES.map(b => (
              <button
                key={b.value}
                onClick={() => changeBlurType(b.value)}
                className={`
                  relative flex flex-col items-center gap-1 p-1 rounded-xl border-2 transition-all
                  ${eff.blurType === b.value
                    ? 'border-primary shadow-sm shadow-primary/20'
                    : 'border-transparent hover:border-border bg-surface-elevated'
                  }
                `}
                title={b.label}
              >
                <div className="w-full h-10">{b.preview}</div>
                <span className={`text-[10px] font-600 ${eff.blurType === b.value ? 'text-primary' : 'text-muted-text'}`}>
                  {b.label}
                </span>
                {eff.blurType === b.value && (
                  <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-primary flex items-center justify-center">
                    <Check size={9} className="text-white" strokeWidth={3} />
                  </div>
                )}
              </button>
            ))}
          </div>

          {/* Blur Strength Slider */}
          <PanelSlider
            label="Blur Strength"
            value={eff.blurStrength}
            min={0} max={100}
            onChange={v => updateEff('blurStrength', v)}
            onCommit={(prev, next) => commitEff('blurStrength', prev, next)}
            accent="#3B82F6"
          />

          {/* Brush Size (only when brush selected) */}
          {(activeLayer?.type === 'brush' || (!activeLayer)) && (
            <PanelSlider
              label="Brush Size"
              value={eff.brushSize}
              min={5} max={120}
              onChange={v => updateEff('brushSize', v)}
              onCommit={(prev, next) => commitEff('brushSize', prev, next)}
              unit="px"
              accent="#8B5CF6"
            />
          )}

          {/* Opacity (only when a layer is selected) */}
          {activeLayer && (
            <PanelSlider
              label="Opacity"
              value={Math.round(eff.opacity * 100)}
              min={0} max={100}
              onChange={v => updateEff('opacity', v / 100)}
              onCommit={(prev, next) => commitEff('opacity', prev / 100, next / 100)}
              accent="#10B981"
            />
          )}

          {/* Color picker (color blur type only) */}
          {eff.blurType === 'color' && (
            <div className="space-y-1.5">
              <span className="text-[11px] font-600 text-secondary-text">Fill Color</span>
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-xl border-2 border-white shadow-md cursor-pointer overflow-hidden relative shrink-0"
                  style={{ background: eff.color }}
                >
                  <input
                    type="color"
                    value={eff.color}
                    onChange={e => updateEff('color', e.target.value)}
                    onBlur={e => commitEff('color', eff.color, e.target.value)}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                </div>
                <div className="flex-1 flex flex-col gap-1">
                  <input
                    type="text"
                    value={eff.color}
                    onChange={e => { if (/^#[0-9a-fA-F]{0,6}$/.test(e.target.value)) updateEff('color', e.target.value); }}
                    className="w-full text-xs font-mono bg-surface-elevated border border-border rounded-lg px-2 py-1.5 outline-none focus:border-primary"
                  />
                  {/* Preset swatches */}
                  <div className="flex gap-1">
                    {['#000000', '#FFFFFF', '#EF4444', '#3B82F6', '#10B981', '#F59E0B'].map(c => (
                      <button
                        key={c}
                        onClick={() => updateEff('color', c)}
                        className="w-5 h-5 rounded-md border border-white/50 shadow-sm transition-transform hover:scale-110"
                        style={{ background: c }}
                        title={c}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Layers List ─────────────────────────────────────────── */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Layers size={14} className="text-muted-text" />
              <span className="text-xs font-700 text-primary-text">Layers</span>
              <span className="text-[10px] bg-surface-elevated text-muted-text font-600 px-1.5 py-0.5 rounded-full">
                {layers.length}
              </span>
            </div>
          </div>

          <div className="space-y-1 max-h-56 overflow-y-auto pr-1">
            {layers.length === 0 ? (
              <div className="text-center py-8 text-muted-text">
                <Square size={24} className="mx-auto mb-2 opacity-30" />
                <p className="text-xs">No layers yet</p>
                <p className="text-[10px] mt-1 opacity-70">Draw a shape to start</p>
              </div>
            ) : (
              layers.map((layer, idx) => (
                <div
                  key={layer.id}
                  onClick={() => setSelectedLayers([layer.id])}
                  className={`
                    group flex items-center gap-2 p-2.5 rounded-xl cursor-pointer transition-all border
                    ${selectedLayerIds.includes(layer.id)
                      ? 'bg-primary/8 border-primary/20 shadow-sm'
                      : 'bg-transparent border-transparent hover:bg-surface-elevated'
                    }
                  `}
                >
                  {/* Type chip */}
                  <div className={`
                    w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-white
                    ${layer.type === 'brush' ? 'bg-purple-500' :
                      layer.type === 'circle' ? 'bg-blue-500' :
                      layer.type === 'polygon' ? 'bg-orange-500' : 'bg-primary'}
                  `}>
                    {layer.type === 'brush' ? <Paintbrush size={12} /> :
                     layer.type === 'circle' ? <Circle size={12} /> :
                     <Square size={12} />}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className={`text-xs font-600 truncate ${selectedLayerIds.includes(layer.id) ? 'text-primary' : 'text-primary-text'}`}>
                      {layer.name}
                    </p>
                    <p className="text-[10px] text-muted-text">
                      {layer.blurType} · {layer.blurStrength}%
                    </p>
                  </div>

                  {/* Controls */}
                  <div className="flex items-center gap-0.5">
                    <button
                      onClick={e => { e.stopPropagation(); updateLayer(layer.id, { visible: !layer.visible }); }}
                      className="p-1 rounded-lg text-muted-text hover:text-primary-text transition-colors"
                    >
                      {layer.visible ? <Eye size={13} /> : <EyeOff size={13} className="opacity-40" />}
                    </button>
                    <button
                      onClick={e => { e.stopPropagation(); updateLayer(layer.id, { locked: !layer.locked }); }}
                      className="p-1 rounded-lg text-muted-text hover:text-primary-text transition-colors"
                    >
                      {layer.locked ? <Lock size={13} /> : <Unlock size={13} className="opacity-40" />}
                    </button>
                    <div className="flex items-center opacity-0 group-hover:opacity-100 transition-opacity gap-0.5">
                      <button
                        onClick={e => { e.stopPropagation(); duplicateLayers([layer.id]); }}
                        className="p-1 rounded-lg text-muted-text hover:text-primary-text"
                      >
                        <Copy size={13} />
                      </button>
                      <button
                        onClick={e => { e.stopPropagation(); deleteLayers([layer.id]); }}
                        className="p-1 rounded-lg text-red-400 hover:text-red-600"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* ── Optional Suggestions ─────────────────────────────────── */}
        {suggestions.length > 0 && (
          <div className="p-4 border-b border-border">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-700 text-primary-text">Suggestions</span>
              <span className="text-[10px] bg-warning/10 text-warning font-600 px-1.5 py-0.5 rounded-full">
                {suggestions.length} optional
              </span>
            </div>
            <div className="space-y-1.5">
              {suggestions.map(suggestion => {
                const isApplied = appliedSuggestions.has(suggestion.id);
                const config = DETECTION_CONFIG[suggestion.type] || {
                  label: suggestion.type,
                  color: '#6c757d',
                };
                return (
                  <div
                    key={suggestion.id}
                    className="flex items-center justify-between p-2.5 rounded-xl border bg-surface-elevated border-border"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <div
                        className="w-6 h-6 rounded-lg flex items-center justify-center shrink-0 text-[10px] font-700 text-white"
                        style={{ background: config.color }}
                      >
                        {suggestion.type.charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-600 text-primary-text truncate">{config.label || suggestion.type}</div>
                        <div className="text-[10px] text-muted-text">{suggestion.confidence}% confidence</div>
                      </div>
                    </div>
                    <button
                      onClick={() => !isApplied && handleApplySuggestion(suggestion)}
                      disabled={isApplied}
                      className={`flex items-center justify-center w-7 h-7 rounded-lg transition-all shrink-0 ${
                        isApplied
                          ? 'bg-success/10 text-success'
                          : 'bg-primary/10 text-primary hover:bg-primary hover:text-white'
                      }`}
                    >
                      {isApplied ? <Check size={13} /> : <Plus size={13} />}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ── Trusted Faces ─────────────────────────────────────────── */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-700 text-primary-text">Trusted Faces</span>
            {trustedFaceImages.length > 0 && (
              <button onClick={() => setTrustedFaceImages([])} className="text-[10px] text-red-400 hover:text-red-600 transition-colors">
                Clear
              </button>
            )}
          </div>
          <div className="flex items-center gap-3">
            {trustedFaceImages.length > 0 ? (
              <div className="flex -space-x-2">
                {trustedFaceImages.slice(0, 4).map((img, i) => (
                  <img key={i} src={img} alt="" className="w-8 h-8 rounded-full object-cover border-2 border-surface" />
                ))}
              </div>
            ) : (
              <div className="w-9 h-9 rounded-full bg-surface-elevated border border-dashed border-border flex items-center justify-center text-muted-text">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                </svg>
              </div>
            )}
            <div className="flex-1">
              <input type="file" accept="image/*" multiple id="trusted-face-panel" className="hidden"
                onChange={async e => {
                  const files = Array.from(e.target.files || []).slice(0, 4);
                  const promises = files.map(f => new Promise<string>(res => {
                    const r = new FileReader();
                    r.onload = ev => res(ev.target?.result as string);
                    r.readAsDataURL(f);
                  }));
                  const imgs = await Promise.all(promises);
                  setTrustedFaceImages([...trustedFaceImages, ...imgs].slice(0, 4));
                }}
              />
              <label htmlFor="trusted-face-panel"
                className="block text-center text-[11px] bg-surface-elevated border border-border rounded-lg px-3 py-2 cursor-pointer hover:bg-[#F0F4F4] transition-colors text-primary-text min-h-[36px] leading-tight"
              >
                {trustedFaceImages.length > 0 ? 'Add More' : 'Upload to whitelist'}
              </label>
            </div>
          </div>
          <p className="text-[10px] text-muted-text mt-2 leading-tight">
            Matching faces won't be auto-blurred. Max 4 images.
          </p>
        </div>

        {/* ── Privacy Score ─────────────────────────────────────────── */}
        {currentResult && (
          <div className="p-4 flex items-center justify-center">
            <PrivacyScoreRing score={currentResult.privacyScore} size={100} />
          </div>
        )}

        {/* ── AI Description ────────────────────────────────────────── */}
        {currentResult?.aiDescription && (
          <div className="px-4 pb-4">
            <div className="bg-primary/5 border border-primary/10 rounded-xl p-3">
              <p className="text-[10px] uppercase tracking-widest font-700 text-primary mb-1.5">AI Analysis</p>
              <p className="text-xs leading-relaxed text-secondary-text">{currentResult.aiDescription}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
