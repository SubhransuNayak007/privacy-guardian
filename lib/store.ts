// lib/store.ts — Zustand global state management
'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { ScanFile, ScanResult, ScanStatus, RecentScan } from '@/types';

interface AppState {
  // Current scan
  currentFile: ScanFile | null;
  currentResult: ScanResult | null;
  scanStatus: ScanStatus;
  scanProgress: number;
  currentStage: string;
  error: string | null;
  isDevMode: boolean;

  // Recent scans
  recentScans: RecentScan[];

  // Trusted Faces (Descriptors as normal arrays to allow serialization)
  enrolledFaces: number[][];

  // Actions
  setFile: (file: ScanFile) => void;
  setResult: (result: ScanResult) => void;
  setScanStatus: (status: ScanStatus) => void;
  setScanProgress: (progress: number) => void;
  setCurrentStage: (stage: string) => void;
  /** Alias for setCurrentStage — used by the pipeline to broadcast active stage */
  updateScanStage: (stage: string) => void;
  setError: (error: string | null) => void;
  setIsDevMode: (active: boolean) => void;
  resetScan: () => void;
  addRecentScan: (scan: RecentScan) => void;
  enrollFace: (descriptor: number[]) => void;
  clearEnrolledFaces: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      currentFile: null,
      currentResult: null,
      scanStatus: 'idle',
      scanProgress: 0,
      currentStage: '',
      error: null,
      isDevMode: false,
      recentScans: [],
      enrolledFaces: [],

      setFile: (file) => set({ currentFile: file }),
      setResult: (result) => set({ currentResult: result }),
      setScanStatus: (status) => set({ scanStatus: status }),
      setScanProgress: (progress) => set({ scanProgress: progress }),
      setCurrentStage: (stage) => set({ currentStage: stage }),
      updateScanStage: (stage) => set({ currentStage: stage }),
      setError: (error) => set({ error }),
      setIsDevMode: (active) => set({ isDevMode: active }),
      resetScan: () =>
        set({
          currentFile: null,
          currentResult: null,
          scanStatus: 'idle',
          scanProgress: 0,
          currentStage: '',
          error: null,
        }),
      addRecentScan: (scan) =>
        set((state) => ({
          recentScans: [scan, ...state.recentScans].slice(0, 10),
        })),
      enrollFace: (descriptor) =>
        set((state) => ({
          enrolledFaces: [...state.enrolledFaces, descriptor],
        })),
      clearEnrolledFaces: () => set({ enrolledFaces: [] }),
    }),
    {
      name: 'privacy-guardian-storage',
      partialize: (state) => ({ enrolledFaces: state.enrolledFaces, recentScans: state.recentScans }),
    }
  )
);
