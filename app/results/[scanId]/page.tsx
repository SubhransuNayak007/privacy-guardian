'use client';

import { useEffect, useState, use } from 'react';
import { useRouter } from 'next/navigation';
import { ResultsScreen } from '@/components/screens/ResultsScreen';
import { useAppStore } from '@/lib/store';
import { getScanSession } from '@/lib/idb';

export default function ResultsPage({ params }: { params: Promise<{ scanId: string }> }) {
  const { scanId } = use(params);
  const router = useRouter();
  const { currentFile, currentResult, setFile, setResult, setScanStatus, setCurrentStage } = useAppStore();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    async function loadSession() {
      // If we already have this exact scan in memory, proceed
      if (currentResult && currentResult.id === scanId && currentFile) {
        setIsReady(true);
        return;
      }

      // Otherwise, attempt to load from IndexedDB
      const session = await getScanSession(scanId);
      if (!session) {
        // Not found anywhere, redirect home
        router.push('/');
        return;
      }

      // We found the session. Reconstruct the blob url from the stored data URL
      try {
        let objectUrl: string;

        if (session.fileDataUrl.startsWith('data:')) {
          // data: URL — convert directly to blob without fetch()
          const [header, base64] = session.fileDataUrl.split(',');
          const mime = header.match(/:(.*?);/)?.[1] || 'image/jpeg';
          const binary = atob(base64);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i);
          }
          const blob = new Blob([bytes], { type: mime });
          objectUrl = URL.createObjectURL(blob);
        } else {
          // Try fetch (works for http/https URLs, may fail for revoked blob: URLs)
          try {
            if (session.fileDataUrl.startsWith('blob:')) {
              throw new Error('Revoked blob URL');
            }
            const res = await fetch(session.fileDataUrl);
            const blob = await res.blob();
            objectUrl = URL.createObjectURL(blob);
          } catch {
            // Blob URL was revoked — can't restore the file preview, go home
            router.push('/');
            return;
          }
        }

        setFile({
          ...session.fileMetadata,
          previewUrl: objectUrl,
        });
        setResult(session.result);
        setScanStatus('complete');
        setCurrentStage('');
        
        setIsReady(true);
      } catch (err) {
        console.error('Failed to restore session', err);
        router.push('/');
      }

    }

    loadSession();
  }, [scanId, currentFile, currentResult, router, setFile, setResult, setScanStatus, setCurrentStage]);

  if (!isReady) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 rounded-full border-4 border-primary border-t-transparent animate-spin" />
          <p className="text-secondary-text font-500 text-sm">Restoring session...</p>
        </div>
      </div>
    );
  }

  return <ResultsScreen scanId={scanId} />;
}
