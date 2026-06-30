'use client';

import dynamic from 'next/dynamic';
import { Navbar } from '@/components/ui/Navbar';
import { Toolbar } from './Toolbar';
import { LayersPanel } from './LayersPanel';
import { ArrowLeft, Download } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { useEffect, useState } from 'react';
import DebugPanel from '@/components/screens/DebugPanel';
import { useEditorStore } from '@/lib/editor-store';

// Dynamically import the CanvasStage because react-konva relies on window/document
// which breaks Next.js SSR.
const CanvasStage = dynamic(() => import('./CanvasStage'), { ssr: false });

export function RedactionStudio() {
  const router = useRouter();
  const { currentFile, currentResult, isDevMode, setIsDevMode } = useAppStore();
  const [mounted, setMounted] = useState(false);
  const [isLayersOpen, setIsLayersOpen] = useState(false);
  const isCompareMode = useEditorStore((state) => state.isCompareMode);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!currentFile) {
      router.push('/');
    }
  }, [currentFile, router]);

  if (!mounted || !currentFile) return null;

  return (
    <div className="h-[100dvh] flex flex-col overflow-hidden bg-[#F9FBFB]">
      <Navbar />
      
      {/* Studio Header */}
      <div className="h-14 bg-surface border-b border-border flex items-center justify-between px-2 sm:px-4 z-20 shadow-sm relative shrink-0">
        <div className="flex items-center gap-2 sm:gap-4">
          <button
            onClick={() => router.push('/')}
            className="flex items-center gap-1 sm:gap-2 text-xs sm:text-sm font-600 text-muted-text hover:text-primary-text transition-colors"
          >
            <ArrowLeft size={16} />
            <span className="hidden sm:inline">Exit Studio</span>
          </button>
          
          <div className="w-[1px] h-6 bg-brand-border" />
          
          <div className="truncate max-w-[120px] sm:max-w-[200px]">
            <h2 className="text-xs sm:text-sm font-700 text-primary-text truncate">{currentFile.name}</h2>
            <p className="text-[9px] sm:text-[10px] text-muted-text font-500">
              {Math.round(currentFile.size / 1024)} KB
            </p>
          </div>

          {currentResult && currentResult.riskScore !== undefined && (
            <>
              <div className="w-[1px] h-6 bg-brand-border hidden sm:block" />
              <div className="hidden sm:flex items-center gap-2 bg-background px-3 py-1.5 rounded-lg border border-border">
                <span className="text-xs font-600 text-muted-text">Risk Score:</span>
                <span className={`text-sm font-700 ${
                  currentResult.riskScore > 75 ? 'text-danger' :
                  currentResult.riskScore > 30 ? 'text-warning' :
                  'text-success'
                }`}>
                  {currentResult.riskScore}
                </span>
                <div className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                  currentResult.riskScore > 75 ? 'bg-danger/10 text-danger' :
                  currentResult.riskScore > 30 ? 'bg-warning/10 text-warning' :
                  'bg-success/10 text-success'
                }`}>
                  {currentResult.riskLevel}
                </div>
              </div>
            </>
          )}
        </div>
        
        <div className="flex items-center gap-1 sm:gap-3">
          <button
            className={`text-xs sm:text-sm font-600 px-2 py-1.5 rounded-lg transition-colors border hidden sm:block ${
              isDevMode
                ? 'bg-danger text-background border-danger'
                : 'text-secondary-text hover:text-primary-text hover:bg-surface-elevated border-transparent'
            }`}
            onClick={() => setIsDevMode(!isDevMode)}
          >
            Debug Detections
          </button>
          <button 
            className={`p-1.5 sm:p-2 rounded-lg border transition-all ${
              isCompareMode 
              ? 'bg-danger text-background border-danger' 
              : 'bg-surface border-border text-primary-text hover:bg-surface-elevated'
            }`}
            onClick={() => {
              const store = useEditorStore.getState();
              store.setIsCompareMode(!store.isCompareMode);
              if (!store.isCompareMode) {
                store.setCompareSliderPos(0.5);
              }
            }}
          >
            <div className="flex items-center gap-2">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <line x1="12" y1="3" x2="12" y2="21" />
              </svg>
              Compare
            </div>
          </button>
          <button 
            className="md:hidden flex items-center justify-center text-secondary-text hover:text-primary-text px-2 py-1.5 rounded-lg hover:bg-surface-elevated"
            onClick={() => setIsLayersOpen(!isLayersOpen)}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 12 12 17 22 12"/><polyline points="2 17 12 22 22 17"/></svg>
          </button>
          <button 
            className="flex items-center gap-1 sm:gap-2 bg-primary text-background px-3 py-1.5 rounded-lg text-xs sm:text-sm font-600 hover:bg-primary-dark transition-colors shadow-sm"
            onClick={() => window.dispatchEvent(new Event('export-canvas'))}
          >
            <Download size={16} />
            <span className="hidden sm:inline">Export</span>
          </button>
        </div>
      </div>

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden relative">
        <Toolbar />
        
        <div className="flex-1 relative overflow-hidden">
          <CanvasStage />
        </div>
        
        <div className={`
          absolute md:relative top-0 right-0 h-full bg-surface z-30 transition-transform duration-300 shadow-xl md:shadow-none
          ${isLayersOpen ? 'translate-x-0' : 'translate-x-full md:translate-x-0'}
        `}>
          <LayersPanel onClose={() => setIsLayersOpen(false)} />
        </div>
        
        {/* Mobile backdrop for layers */}
        {isLayersOpen && (
          <div 
            className="absolute inset-0 bg-primary-text/20 z-20 md:hidden"
            onClick={() => setIsLayersOpen(false)}
          />
        )}
      </div>
      <DebugPanel />
    </div>
  );
}

