"use client";

import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { RedactionStudio } from '@/components/editor/RedactionStudio';
import { useEditorStore, EditorLayer } from '@/lib/editor-store';
import { v4 as uuid } from 'uuid';

export default function EditBlurPage({ params }: { params: Promise<{ scanId: string }> }) {
  const router = useRouter();
  const { scanId } = use(params);
  const { currentResult, currentFile } = useAppStore();
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    if (!currentResult || !currentFile || currentResult.id !== scanId) {
      router.push('/');
      return;
    }

    // Convert detections into EditorLayers
    const { addLayer, setInitialLayers } = useEditorStore.getState();
    
    // We get image dimensions via currentFile or by waiting for it to load
    const img = new window.Image();
    const url = currentFile.previewUrl;
    
    img.onload = () => {
      const w = img.width;
      const h = img.height;
      
      const layers: EditorLayer[] = currentResult.detections.map((det) => {
        const isFace = det.type === 'face';
        
        // Base dimensions
        let lx = (det.bbox.x / 100) * w;
        let ly = (det.bbox.y / 100) * h;
        let lwidth = (det.bbox.width / 100) * w;
        let lheight = (det.bbox.height / 100) * h;

        // Apply 12% expansion padding for faces
        if (isFace) {
          const paddingX = lwidth * 0.12;
          const paddingY = lheight * 0.12;
          lx = Math.max(0, lx - paddingX);
          ly = Math.max(0, ly - paddingY);
          lwidth = Math.min(w - lx, lwidth + paddingX * 2);
          lheight = Math.min(h - ly, lheight + paddingY * 2);
        }

        return {
          id: det.id || uuid(),
          type: isFace ? 'circle' : 'rect',
          x: lx,
          y: ly,
          width: lwidth,
          height: lheight,
          radius: Math.max(lwidth, lheight) / 2,
          blurType: isFace ? 'gaussian' : 'black',
          blurStrength: isFace ? 75 : 100, // 75% maps to 60px Gaussian radius
          opacity: 1,
          locked: false,
          visible: det.redacted,
          name: det.label
        };
      });

      setInitialLayers(layers);
      setIsLoaded(true);
    };
    img.src = url;

  }, [currentResult, currentFile, scanId, router]);

  if (!isLoaded || !currentResult || !currentFile) return null;

  return <RedactionStudio />;
}
