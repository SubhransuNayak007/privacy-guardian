'use client';

import React, { useState, useEffect } from 'react';
import { Shield, Eye, EyeOff, CheckCircle2 } from 'lucide-react';

export function InteractiveDemo() {
  const [isActive, setIsActive] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isActive) {
      setStep(1); // Scanning
      timer = setTimeout(() => {
        setStep(2); // Detected
        timer = setTimeout(() => {
          setStep(3); // Redacted
        }, 1200);
      }, 1200);
    } else {
      setStep(0);
    }
    return () => clearTimeout(timer);
  }, [isActive]);

  return (
    <div className="w-full max-w-3xl mx-auto my-16 p-1 rounded-3xl bg-gradient-to-b from-brand-border to-transparent">
      <div className="bg-background rounded-[23px] overflow-hidden border border-border shadow-xl">
        {/* Header */}
        <div className="bg-surface-elevated px-6 py-4 border-b border-border flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-danger" />
            <div className="w-3 h-3 rounded-full bg-warning" />
            <div className="w-3 h-3 rounded-full bg-success" />
          </div>
          <div className="text-sm font-500 text-secondary-text flex items-center gap-2">
            <Shield size={16} className={step === 3 ? "text-success" : "text-primary"} />
            {step === 0 && "Ready"}
            {step === 1 && "Scanning document..."}
            {step === 2 && "Sensitive data detected"}
            {step === 3 && "Document secured"}
          </div>
        </div>

        {/* Demo Area */}
        <div className="p-8 md:p-12 flex flex-col md:flex-row gap-8 items-center justify-center bg-surface">
          
          {/* Document Simulation */}
          <div className="relative w-full max-w-sm bg-surface-elevated p-6 rounded-xl shadow-sm border border-border">
            {/* Scanning Line overlay */}
            {step === 1 && (
              <div className="absolute left-0 top-0 w-full h-1 bg-primary/50 shadow-[0_0_15px_rgba(23,76,60,0.5)] animate-[slide-up_1.2s_ease-in-out_infinite_alternate]" style={{ zIndex: 20 }} />
            )}

            <div className="space-y-6">
              {/* Header */}
              <div className="flex gap-4 items-center border-b border-border pb-4">
                <div className="w-16 h-16 bg-surface rounded-full flex-shrink-0 relative overflow-hidden">
                  <div className="absolute inset-0 flex items-center justify-center text-secondary-text">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-8 h-8"><path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
                  </div>
                  {/* Face Redaction */}
                  {step >= 2 && (
                    <div className={`absolute inset-0 flex items-center justify-center transition-all duration-500 ${step === 3 ? 'bg-primary-text backdrop-blur-md' : 'bg-danger/20 border-2 border-danger'}`}>
                      {step === 3 && <Shield className="text-background w-6 h-6" />}
                    </div>
                  )}
                </div>
                <div>
                  <div className="h-4 w-32 bg-surface rounded mb-2" />
                  <div className="h-3 w-24 bg-surface rounded" />
                </div>
              </div>

              {/* Data rows */}
              <div className="space-y-4">
                <div className="relative">
                  <div className="text-xs text-secondary-text mb-1">Government ID</div>
                  <div className="font-mono text-sm text-primary-text">4592 1102 9934 0012</div>
                  
                  {step >= 2 && (
                    <div className={`absolute -inset-1 rounded transition-all duration-500 flex items-center px-1 ${step === 3 ? 'bg-primary-text text-background' : 'bg-danger/20 border-2 border-danger'}`}>
                      {step === 3 && <span className="font-mono text-sm">•••• •••• •••• 0012</span>}
                    </div>
                  )}
                </div>

                <div className="relative">
                  <div className="text-xs text-secondary-text mb-1">Phone Number</div>
                  <div className="font-mono text-sm text-primary-text">+1 (555) 019-2834</div>
                  
                  {step >= 2 && (
                    <div className={`absolute -inset-1 rounded transition-all duration-500 flex items-center px-1 ${step === 3 ? 'bg-primary-text text-background' : 'bg-danger/20 border-2 border-danger'}`}>
                      {step === 3 && <span className="font-mono text-sm">+1 (•••) •••-••••</span>}
                    </div>
                  )}
                </div>

                <div className="relative">
                  <div className="text-xs text-secondary-text mb-1">Address</div>
                  <div className="text-sm text-primary-text">123 Privacy Lane, CA 90210</div>
                </div>
              </div>
            </div>
          </div>

          {/* Controls */}
          <div className="flex flex-col gap-4 w-full max-w-xs">
            <button
              onClick={() => setIsActive(!isActive)}
              className={`py-3 px-6 rounded-xl font-600 flex items-center justify-center gap-2 min-h-[44px] transition-all duration-300 shadow-soft ${
                isActive 
                  ? 'bg-surface-elevated text-primary-text border border-border hover:bg-surface' 
                  : 'bg-primary text-background hover:bg-primary-dark shadow-[0_0_15px_rgba(23,76,60,0.4)]'
              }`}
            >
              {isActive ? (
                <>
                  <EyeOff size={18} />
                  Reset Demo
                </>
              ) : (
                <>
                  <Shield size={18} />
                  Run Privacy Engine
                </>
              )}
            </button>
            
            <div className="bg-surface-elevated p-4 rounded-xl border border-border text-sm text-secondary-text">
              <p className="mb-2 font-500 text-primary-text">What happens?</p>
              <ul className="space-y-2">
                <li className={`flex items-center gap-2 transition-opacity ${step >= 1 ? 'opacity-100' : 'opacity-40'}`}>
                  <CheckCircle2 size={16} className={step >= 1 ? 'text-success' : ''} /> 1. Client-side scanning
                </li>
                <li className={`flex items-center gap-2 transition-opacity ${step >= 2 ? 'opacity-100' : 'opacity-40'}`}>
                  <CheckCircle2 size={16} className={step >= 2 ? 'text-success' : ''} /> 2. PII Identification
                </li>
                <li className={`flex items-center gap-2 transition-opacity ${step >= 3 ? 'opacity-100' : 'opacity-40'}`}>
                  <CheckCircle2 size={16} className={step >= 3 ? 'text-success' : ''} /> 3. Secure Redaction
                </li>
              </ul>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

