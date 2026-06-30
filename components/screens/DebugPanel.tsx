'use client';

import React, { useState } from 'react';
import { useAppStore } from '@/lib/store';
import { ChevronDown, ChevronUp, Code, Terminal } from 'lucide-react';

export default function DebugPanel() {
  const isOpen = useAppStore(state => state.isDevMode);
  const setIsOpen = useAppStore(state => state.setIsDevMode);
  // currentScan was renamed to currentResult in the store
  const currentScan = useAppStore(state => state.currentResult);

  if (!currentScan) return null;

  return (
    <div className="fixed bottom-4 left-4 z-50 flex flex-col items-start font-mono text-xs max-w-sm w-full shadow-2xl">
      {isOpen && (
        <div className="bg-surface-elevated text-success p-4 rounded-t-lg w-full h-96 overflow-y-auto border border-border">
          <div className="flex justify-between items-center mb-4 border-b border-border pb-2">
            <h3 className="font-bold flex items-center gap-2"><Terminal size={14}/> Pipeline Debug Log</h3>
          </div>

          <div className="space-y-4">
            {/* Pipeline status */}
            {currentScan.pipelineStatus && (
              <div>
                <p className="text-muted-text uppercase tracking-wider text-[10px] mb-1">Detector Status</p>
                <div className="bg-surface p-2 rounded space-y-1">
                  {(Object.entries(currentScan.pipelineStatus) as [string, string][]).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-muted-text">{k}</span>
                      <span className={v === 'success' ? 'text-success' : v === 'failed' ? 'text-danger' : 'text-muted-text'}>
                        {v}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Pipeline Diagnostics (from Backend) */}
            {currentScan.diagnostics && (
              <div>
                <p className="text-muted-text uppercase tracking-wider text-[10px] mb-1">Stage Diagnostics</p>
                <div className="bg-surface p-2 rounded space-y-2">
                  {(Object.entries(currentScan.diagnostics) as [string, string][]).map(([k, v]) => (
                    <div key={k} className="flex justify-between items-center border-b border-border/50 pb-1 last:border-0 last:pb-0">
                      <span className="text-secondary-text font-bold text-xs">{k}</span>
                      <span className={v.startsWith('✓') ? 'text-success' : 'text-danger'}>
                        {v}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div>
              <p className="text-muted-text uppercase tracking-wider text-[10px] mb-1">Document Classification</p>
              <p className="bg-surface p-2 rounded">{currentScan.documentType ?? '—'}</p>
            </div>

            <div>
              <p className="text-muted-text uppercase tracking-wider text-[10px] mb-1">Risk Score</p>
              <p className={`p-2 rounded font-bold ${currentScan.privacyScore < 50 ? 'bg-danger/10 text-danger' : 'bg-surface'}`}>
                {currentScan.privacyScore}/100 ({currentScan.riskLevel})
              </p>
            </div>

            <div>
              <p className="text-muted-text uppercase tracking-wider text-[10px] mb-1">Detections ({currentScan.detections.length})</p>
              {currentScan.detections.map((d: any, i: number) => (
                <div key={i} className="bg-surface p-2 rounded mb-1 border border-border">
                  <span className="text-warning">[{d.type}]</span> {d.label}
                  <span className="text-muted-text ml-2">Conf: {Math.round(d.confidence || 0)}%</span>
                  {d.text && <p className="text-secondary-text truncate mt-1">&quot;{d.text}&quot;</p>}
                </div>
              ))}
            </div>

            <div>
              <p className="text-muted-text uppercase tracking-wider text-[10px] mb-1">OCR Words ({currentScan.ocrWords?.length || 0})</p>
              <div className="bg-surface p-2 rounded text-muted-text overflow-x-hidden">
                {currentScan.ocrWords?.map((w: any) => w.text).join(' ')}
              </div>
            </div>

            <div>
              <p className="text-muted-text uppercase tracking-wider text-[10px] mb-1">Timing</p>
              <p className="bg-surface p-2 rounded">{(currentScan.processingTime / 1000).toFixed(2)}s</p>
            </div>
          </div>
        </div>
      )}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 bg-surface-elevated text-primary-text px-4 py-2 hover:bg-surface transition-colors border border-border min-h-[44px] min-w-[44px] ${isOpen ? 'rounded-b-lg border-t-0' : 'rounded-lg'}`}
      >
        <Code size={16} className="text-success" />
        <span>Dev Mode</span>
        {isOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
      </button>
    </div>
  );
}
