'use client';

import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, Shield, CheckCircle, Trash2, UploadCloud, Loader2 } from 'lucide-react';
import { useEditorStore } from '@/lib/editor-store';
import { useAppStore } from '@/lib/store';
import { useRouter } from 'next/navigation';
import { v4 as uuidv4 } from 'uuid';

interface TrustedFacesModalProps {
  onClose: () => void;
}

const extractFramesFromVideo = async (file: File): Promise<string[]> => {
  return new Promise((resolve, reject) => {
    const videoUrl = URL.createObjectURL(file);
    const video = document.createElement('video');
    video.src = videoUrl;
    video.muted = true;
    video.playsInline = true;
    video.preload = 'auto'; // Ensure browser loads the video

    // Fallback timeout in case video fails to load or browser blocks it
    const timeout = setTimeout(() => {
      URL.revokeObjectURL(videoUrl);
      reject(new Error('Video frame extraction timed out. Unsupported format?'));
    }, 15000);

    video.onerror = (e) => {
      clearTimeout(timeout);
      URL.revokeObjectURL(videoUrl);
      reject(new Error('Failed to load video. It might be an unsupported format.'));
    };
    
    video.addEventListener('loadedmetadata', async () => {
      try {
        const duration = video.duration || 1;
        // Extract 4 frames spread across the video
        const timestamps = [duration * 0.2, duration * 0.4, duration * 0.6, duration * 0.8];
        const frames: string[] = [];
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        for (const time of timestamps) {
          await new Promise<void>((seekResolve, seekReject) => {
            const seekTimeout = setTimeout(() => seekReject(new Error('Seek timeout')), 5000);
            
            const onSeeked = () => {
              clearTimeout(seekTimeout);
              video.removeEventListener('seeked', onSeeked);
              video.removeEventListener('error', onError);
              if (ctx) {
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                frames.push(canvas.toDataURL('image/jpeg', 0.8));
              }
              seekResolve();
            };
            
            const onError = () => {
              clearTimeout(seekTimeout);
              video.removeEventListener('seeked', onSeeked);
              video.removeEventListener('error', onError);
              seekReject(new Error('Error seeking video'));
            };
            
            video.addEventListener('seeked', onSeeked);
            video.addEventListener('error', onError);
            video.currentTime = time;
          });
        }
        
        clearTimeout(timeout);
        URL.revokeObjectURL(videoUrl);
        resolve(frames.slice(0, 4));
      } catch (err) {
        clearTimeout(timeout);
        URL.revokeObjectURL(videoUrl);
        reject(err);
      }
    });
    
    video.load();
  });
};

const extractImages = async (files: File[]): Promise<string[]> => {
  const images = files.filter(f => f.type.startsWith('image/')).slice(0, 4);
  const promises = images.map(file => {
    return new Promise<string>((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          const canvas = document.createElement('canvas');
          const MAX_DIM = 800;
          let { width, height } = img;
          if (width > MAX_DIM || height > MAX_DIM) {
            if (width > height) {
              height = Math.round((height * MAX_DIM) / width);
              width = MAX_DIM;
            } else {
              width = Math.round((width * MAX_DIM) / height);
              height = MAX_DIM;
            }
          }
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d');
          ctx?.drawImage(img, 0, 0, width, height);
          resolve(canvas.toDataURL('image/jpeg', 0.8));
        };
        img.src = e.target?.result as string;
      };
      reader.readAsDataURL(file);
    });
  });
  return Promise.all(promises);
};

export function TrustedFacesModal({ onClose }: TrustedFacesModalProps) {
  const { trustedFaceImages, setTrustedFaceImages } = useEditorStore();
  const currentFile = useAppStore(state => state.currentFile);
  const router = useRouter();
  
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [mounted, setMounted] = useState(false);
  
  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  const handleFiles = async (files: File[]) => {
    if (!files.length) return;
    
    setIsProcessing(true);
    let newFaces: string[] = [];

    try {
      const videoFile = files.find(f => f.type.startsWith('video/'));
      if (videoFile) {
        newFaces = await extractFramesFromVideo(videoFile);
      } else {
        newFaces = await extractImages(files);
      }
      
      if (newFaces.length > 0) {
        const combined = [...trustedFaceImages, ...newFaces].slice(0, 4);
        setTrustedFaceImages(combined);
        setSuccessMsg(`Successfully enrolled ${newFaces.length} face image(s)!`);
        setTimeout(() => setSuccessMsg(null), 3000);
      }
    } catch (err: any) {
      console.error('Error extracting faces:', err);
      alert(`Error extracting faces: ${err.message || 'Unknown error'}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    await handleFiles(files);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files || []);
    await handleFiles(files);
  };

  const handleClear = () => {
    if (confirm('Are you sure you want to remove all trusted faces?')) {
      setTrustedFaceImages([]);
      setSuccessMsg('Trusted faces removed.');
      setTimeout(() => setSuccessMsg(null), 3000);
    }
  };

  const handleRemoveOne = (index: number) => {
    const next = [...trustedFaceImages];
    next.splice(index, 1);
    setTrustedFaceImages(next);
  };

  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-primary-text/60 backdrop-blur-sm">
      <div className="bg-surface rounded-2xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-surface-elevated/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-semibold text-primary-text">Trusted Faces</h2>
              <p className="text-xs text-muted-text">Biometric enrollment</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="min-w-[44px] min-h-[44px] flex items-center justify-center text-secondary-text hover:text-primary-text hover:bg-surface-elevated rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 flex-1 overflow-y-auto">
          <p className="text-sm text-secondary-text mb-6 leading-relaxed">
            Enroll your face or trusted family members. The AI will learn these faces and <strong>skip blurring them</strong> during scans, while continuing to redact strangers to protect their privacy. 
          </p>

          <div className="bg-brand-accent/10 border border-brand-accent/20 rounded-xl p-4 mb-6 flex gap-3 text-sm text-brand-accent">
            <Shield className="w-5 h-5 shrink-0 text-brand-accent" />
            <p>
              Your face descriptors are stored <strong>locally on your device</strong>. No biometric data ever leaves your browser.
            </p>
          </div>

          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-primary-text">Enrolled Profiles</span>
              <span className="bg-surface-elevated text-primary-text px-2.5 py-0.5 rounded-full font-medium">
                {trustedFaceImages.length} / 4
              </span>
            </div>

            {/* Success Message */}
            {successMsg && (
              <div className="flex items-start gap-2 text-sm text-primary bg-primary/10 p-3 rounded-lg border border-primary/20">
                <CheckCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <p>{successMsg}</p>
              </div>
            )}

            {trustedFaceImages.length > 0 && (
              <div className="border border-border rounded-xl p-4 bg-background/30">
                 <div className="flex items-center justify-between mb-3">
                   <div>
                     <h3 className="text-sm font-semibold text-primary-text">Active Profiles</h3>
                     <p className="text-xs text-secondary-text mt-1">These faces will bypass redaction.</p>
                   </div>
                   <button onClick={handleClear} className="min-w-[44px] min-h-[44px] flex items-center justify-center text-danger hover:bg-danger/10 rounded-lg transition-colors" title="Clear all">
                     <Trash2 className="w-5 h-5" />
                   </button>
                 </div>
                 <div className="grid grid-cols-4 gap-2">
                   {trustedFaceImages.map((img, i) => (
                     <div key={i} className="relative group aspect-square">
                       <img src={img} alt={`Trusted Face ${i+1}`} className="w-full h-full rounded-lg object-cover border-2 border-primary/30" />
                       <button 
                         onClick={() => handleRemoveOne(i)}
                         className="absolute -top-3 -right-3 flex items-center justify-center min-w-[44px] min-h-[44px] opacity-0 group-hover:opacity-100 transition-opacity"
                       >
                         <div className="bg-danger text-background rounded-full p-1 shadow-sm">
                           <X className="w-3 h-3" />
                         </div>
                       </button>
                     </div>
                   ))}
                 </div>
              </div>
            )}
            
            {trustedFaceImages.length < 4 && (
              <div 
                className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center gap-4 text-center transition-colors relative overflow-hidden ${
                  isDragging 
                    ? 'border-primary bg-primary/5' 
                    : 'border-border bg-background/50 hover:bg-background'
                }`}
                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
              >
                <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                  {isProcessing ? <Loader2 className="w-7 h-7 animate-spin" /> : <UploadCloud className="w-7 h-7" />}
                </div>
                <div>
                  <h3 className="text-base font-semibold text-primary-text mb-1">
                    {isProcessing ? 'Processing...' : 'Upload Faces or Video'}
                  </h3>
                  <p className="text-sm text-secondary-text max-w-sm">
                    {isProcessing ? 'Extracting frames...' : 'Select up to 4 images, or a short video of the face.'}
                  </p>
                </div>
                {!isProcessing && (
                  <input 
                    type="file" 
                    accept="image/*,video/*" 
                    multiple
                    onChange={handleFileUpload}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                    title="Upload face images or video"
                  />
                )}
              </div>
            )}
            
            <div className="pt-2">
              <button 
                onClick={() => {
                  if (currentFile) {
                    router.push(`/scanning/${uuidv4()}`);
                  }
                  onClose();
                }}
                className="w-full py-2.5 min-h-[44px] bg-primary text-background text-sm font-semibold rounded-lg hover:bg-primary-dark transition-colors flex items-center justify-center gap-2"
              >
                {currentFile ? 'Save & Re-Analyze Document' : 'Save & Continue'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}

