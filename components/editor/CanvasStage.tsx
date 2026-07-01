import React, { useRef, useState, useEffect, useMemo } from 'react';
import Konva from 'konva';
import { Stage, Layer, Image as KonvaImage, Rect, Circle, Transformer, Line, Group, Text } from 'react-konva';
import useImage from 'use-image';
import { useEditorStore } from '@/lib/editor-store';
import { useAppStore } from '@/lib/store';
import { v4 as uuid } from 'uuid';
import { BlurEngine } from './BlurEngine';
import { useSearchParams } from 'next/navigation';

// Helper component for individual layers to handle selection/transformers
const RedactionShape = ({ 
  layer, 
  image,
  isSelected, 
  onSelect, 
  onChange,
  onCommit
}: { 
  layer: any; 
  image: HTMLImageElement | undefined;
  isSelected: boolean; 
  onSelect: () => void; 
  onChange: (newAttrs: any) => void;
  onCommit: (prev: any, next: any) => void;
}) => {
  const shapeRef = useRef<any>(null);
  const trRef = useRef<any>(null);

  const [startState, setStartState] = useState<any>(null);

  useEffect(() => {
    if (isSelected && trRef.current && shapeRef.current) {
      trRef.current.nodes([shapeRef.current]);
      trRef.current.getLayer().batchDraw();
    }
  }, [isSelected]);

  // Determine fill/stroke based on blur type for the interactive mask
  // We use almost transparent so it catches events but doesn't obscure the blur beneath
  const getFill = () => {
    return 'rgba(0,0,0,0.01)';
  };

  const handleDragStart = () => {
    setStartState({ x: layer.x, y: layer.y });
  };

  const handleDragMove = (e: any) => {
    onChange({ x: e.target.x(), y: e.target.y() });
  };

  const handleDragEnd = (e: any) => {
    const next = { x: e.target.x(), y: e.target.y() };
    onChange(next);
    if (startState) {
      onCommit(startState, next);
      setStartState(null);
    }
  };

  const handleTransformStart = () => {
    setStartState({
      x: layer.x,
      y: layer.y,
      width: layer.width,
      height: layer.height,
      radius: layer.radius,
      rotation: layer.rotation || 0
    });
  };

  const handleTransform = (e: any) => {
    const node = shapeRef.current;
    if (!node) return;
    
    const scaleX = node.scaleX();
    const scaleY = node.scaleY();
    
    node.scaleX(1);
    node.scaleY(1);
    
    onChange({
      x: node.x(),
      y: node.y(),
      width: Math.max(5, (node.width() || 0) * scaleX),
      height: layer.type === 'rect' ? Math.max(5, (node.height() || 0) * scaleY) : undefined,
      radius: layer.type === 'circle' ? Math.max(5, (node.radius?.() || 0) * scaleX) : undefined,
      rotation: node.rotation()
    });
  };

  const handleTransformEnd = (e: any) => {
    const node = shapeRef.current;
    const scaleX = node.scaleX();
    const scaleY = node.scaleY();
    
    node.scaleX(1);
    node.scaleY(1);
    
    const next = {
      x: node.x(),
      y: node.y(),
      width: Math.max(5, (node.width() || 0) * scaleX),
      height: layer.type === 'rect' ? Math.max(5, (node.height() || 0) * scaleY) : undefined,
      radius: layer.type === 'circle' ? Math.max(5, (node.radius?.() || 0) * scaleX) : undefined,
      rotation: node.rotation()
    };
    
    onChange(next);
    if (startState) {
      onCommit(startState, next);
      setStartState(null);
    }
  };

  if (!layer.visible) return null;

  return (
    <React.Fragment>
      {/* Render the actual visual effect */}
      {image && <BlurEngine layer={layer} image={image} />}

      {/* Render the interactive, transparent shape on top */}
      {layer.type === 'rect' && (
        <Rect
          ref={shapeRef}
          x={layer.x}
          y={layer.y}
          width={layer.width}
          height={layer.height}
          rotation={layer.rotation || 0}
          cornerRadius={layer.cornerRadius || 0}
          fill={getFill()}
          opacity={1} // Keep at 1, fill is already almost transparent
          draggable={!layer.locked}
          onClick={onSelect}
          onTap={onSelect}
          onDragStart={handleDragStart}
          onDragMove={handleDragMove}
          onDragEnd={handleDragEnd}
          onTransformStart={handleTransformStart}
          onTransform={handleTransform}
          onTransformEnd={handleTransformEnd}
          hitStrokeWidth={10}
        />
      )}
      
      {layer.type === 'circle' && (
        <Circle
          ref={shapeRef}
          x={layer.x}
          y={layer.y}
          radius={Math.abs(layer.radius || 0)}
          rotation={layer.rotation || 0}
          fill={getFill()}
          opacity={1}
          draggable={!layer.locked}
          onClick={onSelect}
          onTap={onSelect}
          onDragStart={handleDragStart}
          onDragMove={handleDragMove}
          onDragEnd={handleDragEnd}
          onTransformStart={handleTransformStart}
          onTransform={handleTransform}
          onTransformEnd={handleTransformEnd}
          hitStrokeWidth={10}
        />
      )}

      {layer.type === 'brush' && (
        <Line
          ref={shapeRef}
          points={layer.points}
          stroke={getFill()}
          strokeWidth={(layer.brushSize || 20) * (image ? Math.max(image.width, image.height)/1000 : 1)}
          tension={0.5}
          lineCap="round"
          lineJoin="round"
          draggable={!layer.locked}
          onClick={onSelect}
          onTap={onSelect}
          onDragStart={handleDragStart}
          onDragMove={handleDragMove}
          onDragEnd={handleDragEnd}
        />
      )}
      
      {isSelected && !layer.locked && (
        <Transformer
          ref={trRef}
          boundBoxFunc={(oldBox, newBox) => {
            if (newBox.width < 5 || newBox.height < 5) {
              return oldBox;
            }
            return newBox;
          }}
        />
      )}
    </React.Fragment>
  );
};

export default function CanvasStage() {
  const { currentFile, currentResult } = useAppStore();
  const [image] = useImage(currentFile?.previewUrl || '');
  
  const searchParams = useSearchParams();
  const isDebug = searchParams?.get('debug') === 'true';

  const { 
    zoom, pan, setPan, currentTool, layers, showOriginal,
    isCompareMode, compareSliderPos, setCompareSliderPos,
    selectedLayerIds, setSelectedLayers, addLayer, updateLayer, commitLayerUpdate,
    defaultBlurType, defaultBlurStrength, defaultBrushSize, defaultColor
  } = useEditorStore();
  
  const [isDrawing, setIsDrawing] = useState(false);
  const [newShape, setNewShape] = useState<any>(null);
  const [hasFittedImage, setHasFittedImage] = useState(false);
  
  const [stageSize, setStageSize] = useState({ width: 800, height: 600 });
  const containerRef = useRef<HTMLDivElement>(null);

  // Auto-fit image when it loads
  useEffect(() => {
    if (image && stageSize.width > 0 && stageSize.height > 0 && !hasFittedImage) {
      const padding = 40;
      const fitScaleX = (stageSize.width - padding) / image.width;
      const fitScaleY = (stageSize.height - padding) / image.height;
      const fitScale = Math.min(fitScaleX, fitScaleY, 1);
      
      useEditorStore.getState().setZoom(fitScale);
      
      const scaledWidth = image.width * fitScale;
      const scaledHeight = image.height * fitScale;
      useEditorStore.getState().setPan({
        x: (stageSize.width - scaledWidth) / 2,
        y: (stageSize.height - scaledHeight) / 2
      });
      
      setHasFittedImage(true);
    }
  }, [image, stageSize, hasFittedImage]);

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setStageSize({
          width: containerRef.current.offsetWidth,
          height: containerRef.current.offsetHeight
        });
      }
    };
    
    // Initial size
    updateSize();
    
    // Listen to resize events
    window.addEventListener('resize', updateSize);
    
    // Setup ResizeObserver for the container as a fallback for layout shifts
    let observer: ResizeObserver;
    if (containerRef.current && window.ResizeObserver) {
      observer = new ResizeObserver(updateSize);
      observer.observe(containerRef.current);
    }
    
    return () => {
      window.removeEventListener('resize', updateSize);
      if (observer) observer.disconnect();
    };
  }, []);

  const imageWidth = image ? image.width : 1;
  const imageHeight = image ? image.height : 1;

  const stageRef = useRef<any>(null);
  const exportStageRef = useRef<any>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger if user is typing in an input field
      if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') return;

      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        if (e.shiftKey) {
          useEditorStore.getState().redo();
        } else {
          useEditorStore.getState().undo();
        }
        e.preventDefault();
      } else if ((e.ctrlKey || e.metaKey) && e.key === 'y') {
        useEditorStore.getState().redo();
        e.preventDefault();
      } else if (e.key === 'Delete' || e.key === 'Backspace') {
        const selected = useEditorStore.getState().selectedLayerIds;
        if (selected.length > 0) {
          useEditorStore.getState().deleteLayers(selected);
        }
      } else if (e.key === 'Escape') {
        useEditorStore.getState().clearSelection();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Auto-apply all detections as blur layers when a new scan result arrives
  const appliedResultIdRef = useRef<string | null>(null);
  useEffect(() => {
    if (currentResult && currentFile && image && appliedResultIdRef.current !== currentResult.id) {
      appliedResultIdRef.current = currentResult.id;
      
      const imgW = image.width;
      const imgH = image.height;
      
      currentResult.detections.forEach(det => {
        if (!det.redacted || det.bbox.width <= 0 || det.bbox.height <= 0) return;
        let adaptiveBlur = 30;
        const dt = (det.type || '').toLowerCase();
        const dl = (det.label || '').toLowerCase();
        
        if (dt.includes('nsfw') || dl.includes('nsfw'))  adaptiveBlur = 80; // Maximum blur for NSFW
        else if (dt.includes('weapon') || dl.includes('weapon')) adaptiveBlur = 60;
        else if (dt.includes('face') || dl.includes('face')) adaptiveBlur = 32;
        else if (dt.includes('signature') || dl.includes('signature')) adaptiveBlur = 40;
        else if (dt.includes('passport') || dt.includes('document') || dt.includes('id') || dt.includes('plate') || dl.includes('passport') || dl.includes('document') || dl.includes('id') || dl.includes('plate')) adaptiveBlur = 64;
        else if (dt.includes('text') || dl.includes('text') || dl.includes('regex') || dl.includes('ner') || dl.includes('multi')) adaptiveBlur = 18;
        
        useEditorStore.getState().addLayer({
          type: det.polygon ? 'polygon' : 'rect',
          x: (det.bbox.x / 100) * imgW,
          y: (det.bbox.y / 100) * imgH,
          width: (det.bbox.width / 100) * imgW,
          height: (det.bbox.height / 100) * imgH,
          polygon: det.polygon ? det.polygon.flatMap(p => [(p.x / 100) * imgW, (p.y / 100) * imgH]) : undefined,
          cornerRadius: det.type === 'face' ? Math.max((det.bbox.width / 100) * imgW, (det.bbox.height / 100) * imgH) / 2 : 4,
          blurType: 'gaussian', // Make everything gaussian by default
          color: '#000000',
          blurStrength: adaptiveBlur, // Adaptive blur radius based on type
          opacity: 1,
          visible: true,
          locked: false,
        });
      });
    }
  }, [currentResult, currentFile, image]);

  useEffect(() => {
    const handleExport = () => {
      if (exportStageRef.current) {
        // Wait for state to update, then export from the hidden 1:1 stage
        setTimeout(() => {
          const uri = exportStageRef.current.toDataURL({ pixelRatio: 1 });
          const link = document.createElement('a');
          link.download = `privacy-guardian-redacted-${Date.now()}.png`;
          link.href = uri;
          link.click();
        }, 100);
      }
    };
    window.addEventListener('export-canvas', handleExport);
    return () => window.removeEventListener('export-canvas', handleExport);
  }, []);

  const getPointerPos = () => {
    const stage = stageRef.current;
    if (!stage) return { x: 0, y: 0 };
    const pos = stage.getPointerPosition();
    return {
      x: (pos.x - pan.x) / zoom,
      y: (pos.y - pan.y) / zoom,
    };
  };

  const handleMouseDown = (e: any) => {
    if (showOriginal) return;

    // If clicking on a shape (not stage), let the shape's onClick handle it unless drawing
    const clickedOnEmpty = e.target === e.target.getStage() || e.target.hasName('bg-image');
    
    if (clickedOnEmpty && currentTool === 'select') {
      setSelectedLayers([]);
      return;
    }

    if (currentTool === 'rectangle' || currentTool === 'circle' || currentTool === 'rounded-rectangle' || currentTool === 'brush') {
      setIsDrawing(true);
      const pos = getPointerPos();
      
      if (currentTool === 'brush') {
        setNewShape({
          type: 'brush',
          points: [pos.x, pos.y, pos.x, pos.y],
          blurStrength: defaultBlurStrength,
          brushSize: defaultBrushSize
        });
      } else {
        setNewShape({
          type: currentTool === 'rectangle' || currentTool === 'rounded-rectangle' ? 'rect' : 'circle',
          x: pos.x,
          y: pos.y,
          width: 0,
          height: 0,
          radius: 0,
          cornerRadius: currentTool === 'rounded-rectangle' ? 16 : 0
        });
      }
      
      // Clear selection while drawing
      setSelectedLayers([]);
    }
  };

  const handleMouseMove = (e: any) => {
    if (!isDrawing || !newShape) return;
    
    const pos = getPointerPos();
    
    if (newShape.type === 'rect') {
      setNewShape({
        ...newShape,
        width: pos.x - (newShape.x || 0),
        height: pos.y - (newShape.y || 0),
      });
    } else if (newShape.type === 'circle') {
      const radius = Math.sqrt(Math.pow(pos.x - (newShape.x || 0), 2) + Math.pow(pos.y - (newShape.y || 0), 2));
      setNewShape({
        ...newShape,
        radius,
      });
    } else if (newShape.type === 'brush') {
      setNewShape({
        ...newShape,
        points: [...(newShape.points || []), pos.x, pos.y]
      });
    }
  };

  const handleMouseUp = () => {
    if (!isDrawing || !newShape) return;
    setIsDrawing(false);
    
    // Validate shape size
    let isValid = false;
    if (newShape.type === 'rect' && Math.abs(newShape.width || 0) > 5 && Math.abs(newShape.height || 0) > 5) isValid = true;
    if (newShape.type === 'circle' && (newShape.radius || 0) > 5) isValid = true;
    if (newShape.type === 'brush' && (newShape.points?.length || 0) > 2) isValid = true;

    if (isValid) {
      // Normalize negative width/height
      const finalShape = { ...newShape };
      if (finalShape.type === 'rect') {
        if (finalShape.width < 0) {
          finalShape.x += finalShape.width;
          finalShape.width = Math.abs(finalShape.width);
        }
        if (finalShape.height < 0) {
          finalShape.y += finalShape.height;
          finalShape.height = Math.abs(finalShape.height);
        }
      }
      
      addLayer({
        ...finalShape,
        cornerRadius: finalShape.cornerRadius || 0,
        blurType: defaultBlurType,
        color: defaultColor,
        blurStrength: defaultBlurStrength,
        brushSize: defaultBrushSize,
        opacity: 1,
        visible: true,
        locked: false
      });
    }
    
    setNewShape(null);
  };

  // Map double clicks on the image to OCR smart selection
  const handleDblClick = (e: any) => {
    if (currentTool !== 'select') return;
    
    // Normally we'd do a hit test against the OCR bounding boxes here
    // For now, let's just log it. (Implementation details for Phase 4)
    console.log("Double clicked image at", getPointerPos());
  };

  return (
    <div className="flex-1 overflow-hidden bg-[#e5e5e5] relative" id="stage-container" ref={containerRef}>
      <Stage 
        ref={stageRef}
        width={stageSize.width}
        height={stageSize.height}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onDblClick={handleDblClick}
        scaleX={zoom}
        scaleY={zoom}
        x={pan.x}
        y={pan.y}
        draggable={currentTool === 'select' && !isDrawing} // pan with drag
        onDragEnd={(e) => {
          if (e.target === stageRef.current) {
            setPan({ x: e.target.x(), y: e.target.y() });
          }
        }}
      >
        <Layer>
          {image && (
            <KonvaImage 
              image={image} 
              name="bg-image"
              // In a real implementation, we would scale the image to fit the stage 
              // and convert the BoundingBoxes correctly.
            />
          )}
          
          <Group
            clipFunc={isCompareMode ? (ctx) => {
              const containerWidth = stageSize.width;
              const screenX = compareSliderPos * containerWidth;
              const stageX = (screenX - pan.x) / zoom;
              
              ctx.beginPath();
              ctx.rect(stageX, -999999, 9999999, 9999999);
              ctx.closePath();
            } : undefined}
          >
            {!showOriginal && layers.map(layer => (
              <RedactionShape
                key={layer.id}
                layer={layer}
                image={image}
                isSelected={selectedLayerIds.includes(layer.id)}
                onSelect={() => {
                  if (currentTool === 'select') {
                    setSelectedLayers([layer.id]);
                  }
                }}
                onChange={(newAttrs) => updateLayer(layer.id, newAttrs)}
                onCommit={(prev, next) => commitLayerUpdate(layer.id, prev, next)}
              />
            ))}

            {/* OCR Hit Test Layer */}
            {!showOriginal && useAppStore.getState().currentResult?.ocrWords
              ?.filter((word: any) => word && word.bbox && isFinite(word.bbox.x) && isFinite(word.bbox.y) && isFinite(word.bbox.width) && isFinite(word.bbox.height) && word.bbox.width > 0 && word.bbox.height > 0)
              .map((word: any, index: number) => (
              <Rect
                key={`ocr-word-${index}-${(word.text || '').slice(0, 8)}`}
                x={word.bbox.x * imageWidth}
                y={word.bbox.y * imageHeight}
                width={word.bbox.width * imageWidth}
                height={word.bbox.height * imageHeight}
                fill="transparent"

                onDblClick={(e) => {
                  e.cancelBubble = true;
                  if (currentTool !== 'select') return;
                  
                  const pad = 6;
                  addLayer({
                    type: 'rect',
                    x: (word.bbox.x * imageWidth) - pad,
                    y: (word.bbox.y * imageHeight) - pad,
                    width: (word.bbox.width * imageWidth) + (pad * 2),
                    height: (word.bbox.height * imageHeight) + (pad * 2),
                    cornerRadius: 4,
                    blurType: 'black',
                    color: '#000000',
                    blurStrength: 100,
                    opacity: 1,
                    visible: true,
                    locked: false
                  });
                  // Auto-select the newly created layer (store prepends it)
                  const newLayers = useEditorStore.getState().layers;
                  if (newLayers.length > 0) setSelectedLayers([newLayers[0].id]);
                }}
                onMouseEnter={(e) => {
                  if (currentTool === 'select') {
                    const container = e.target.getStage()?.container();
                    if (container) {
                      container.style.cursor = 'crosshair';
                      (e.target as Konva.Shape).stroke('rgba(0, 150, 255, 0.5)');
                      (e.target as Konva.Shape).strokeWidth(2 / zoom);
                    }
                  }
                }}
                onMouseLeave={(e) => {
                  if (currentTool === 'select') {
                    const container = e.target.getStage()?.container();
                    if (container) {
                      container.style.cursor = 'default';
                      (e.target as Konva.Shape).strokeWidth(0);
                    }
                  }
                }}
              />
            ))}
          </Group>

          {/* Drawing Preview Layer */}
          {!showOriginal && newShape && (
            <>
              {newShape.type === 'rect' && (
                <Rect
                  x={newShape.width < 0 ? newShape.x + newShape.width : newShape.x}
                  y={newShape.height < 0 ? newShape.y + newShape.height : newShape.y}
                  width={Math.abs(newShape.width)}
                  height={Math.abs(newShape.height)}
                  cornerRadius={newShape.cornerRadius}
                  fill="rgba(100, 100, 100, 0.4)"
                  stroke="#1E8449"
                  strokeWidth={2}
                  dash={[5, 5]}
                />
              )}
              {newShape.type === 'circle' && (
                <Circle
                  x={newShape.x}
                  y={newShape.y}
                  radius={Math.abs(newShape.radius || 0)}
                  fill="rgba(100, 100, 100, 0.4)"
                  stroke="#1E8449"
                  strokeWidth={2}
                  dash={[5, 5]}
                />
              )}
              {newShape && newShape.type === 'brush' && (
                <Line
                  points={newShape.points || []}
                  stroke="rgba(0,0,0,0.3)"
                  strokeWidth={(newShape.brushSize || 20) * (image ? Math.max(image.width, image.height)/1000 : 1)}
                  tension={0.5}
                  lineCap="round"
                  lineJoin="round"
                />
              )}
            </>
          )}

          {/* Debug Overlay Bounding Boxes — 3-tier confidence visualization */}
          {isDebug && currentResult && (
            <Group>
              {currentResult.detections.map((det: any) => {
                const boxX = (det.bbox.x / 100) * imageWidth;
                const boxY = (det.bbox.y / 100) * imageHeight;
                const boxW = (det.bbox.width / 100) * imageWidth;
                const boxH = (det.bbox.height / 100) * imageHeight;
                // Industry-standard 3-tier color coding (matches Google DLP / AWS Rekognition UI):
                // ≥78% auto-redacted  → RED solid   (VERY_LIKELY / LIKELY)
                // 55–78% suggestion   → YELLOW dash  (POSSIBLE)
                // <55% (faces only)   → ORANGE       (face fallback)
                const isFace = det.type === 'face';
                const isAutoRedact = det.redacted;
                const color = isFace
                  ? '#EF4444'                           // red for faces
                  : isAutoRedact
                    ? '#3B82F6'                         // blue for confirmed text detections
                    : '#F59E0B';                        // amber for suggestions
                const isDash = !isAutoRedact && !isFace; // dashed for suggestions
                const typeLabel = det.type.toUpperCase().replace('_', ' ');
                const statusLabel = isAutoRedact ? '●' : '◌';
                return (
                  <Group key={`debug-${det.id}`} x={boxX} y={boxY}>
                    <Rect
                      width={boxW}
                      height={boxH}
                      stroke={color}
                      strokeWidth={2.5 / zoom}
                      dash={isDash ? [6 / zoom, 3 / zoom] : undefined}
                      fill={isAutoRedact ? `${color}10` : 'transparent'}
                    />
                    <Rect
                      y={-22 / zoom}
                      width={Math.min(boxW, 160 / zoom)}
                      height={22 / zoom}
                      fill={color}
                      cornerRadius={3 / zoom}
                    />
                    <Text
                      y={-18 / zoom}
                      x={4 / zoom}
                      text={`${statusLabel} ${typeLabel}: ${det.confidence.toFixed(0)}%`}
                      fontSize={11 / zoom}
                      fill="white"
                      fontStyle="bold"
                    />
                  </Group>
                );
              })}
            </Group>
          )}
        </Layer>
      </Stage>

      {/* Compare Slider UI */}
      {isCompareMode && (
        <div
          className="absolute top-0 bottom-0 w-1 bg-background cursor-ew-resize z-40 flex items-center justify-center shadow-[0_0_10px_rgba(0,0,0,0.5)]"
          style={{ left: `${compareSliderPos * 100}%`, transform: 'translateX(-50%)' }}
          onMouseDown={(e) => {
            const onMouseMove = (ev: MouseEvent) => {
              const container = document.getElementById('stage-container');
              if (!container) return;
              const rect = container.getBoundingClientRect();
              const x = ev.clientX - rect.left;
              const pos = Math.max(0, Math.min(1, x / rect.width));
              setCompareSliderPos(pos);
            };
            const onMouseUp = () => {
              window.removeEventListener('mousemove', onMouseMove);
              window.removeEventListener('mouseup', onMouseUp);
              document.body.style.cursor = 'default';
            };
            document.body.style.cursor = 'ew-resize';
            window.addEventListener('mousemove', onMouseMove);
            window.addEventListener('mouseup', onMouseUp);
          }}
          onTouchStart={(e) => {
            const onTouchMove = (ev: TouchEvent) => {
              const container = document.getElementById('stage-container');
              if (!container) return;
              const rect = container.getBoundingClientRect();
              const x = ev.touches[0].clientX - rect.left;
              const pos = Math.max(0, Math.min(1, x / rect.width));
              setCompareSliderPos(pos);
            };
            const onTouchEnd = () => {
              window.removeEventListener('touchmove', onTouchMove);
              window.removeEventListener('touchend', onTouchEnd);
            };
            window.addEventListener('touchmove', onTouchMove, { passive: true });
            window.addEventListener('touchend', onTouchEnd);
          }}
        >
          <div className="w-8 h-8 min-h-[44px] min-w-[44px] bg-surface-elevated rounded-full shadow-lg border border-border flex items-center justify-center text-secondary-text hover:scale-110 transition-transform">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 8L22 12L18 16M6 8L2 12L6 16" />
            </svg>
          </div>
        </div>
      )}

      {/* Debug Information Panel */}
      {isDebug && (
        <div className="absolute top-4 left-4 bg-surface-elevated text-success p-4 rounded text-xs font-mono z-50 pointer-events-none w-80 shadow-lg border border-success/30 overflow-hidden">
          <h3 className="text-primary-text font-bold mb-2 border-b border-success/30 pb-1">PIPELINE DEBUG OVERLAY</h3>
          <div className="space-y-1">
            <p><span className="text-muted-text">Orig Image:</span> {imageWidth} × {imageHeight}</p>
            <p><span className="text-muted-text">Canvas Stage:</span> {Math.round(window.innerWidth - 376)} × {Math.round(window.innerHeight - 64)}</p>
            <p><span className="text-muted-text">Scale (Zoom):</span> {zoom.toFixed(2)}x</p>
            {currentResult?.detections?.slice(0, 3).map((det: any, i: number) => (
              <div key={i} className="mt-2 pt-2 border-t border-success/20">
                <p className="text-primary-text font-bold">{det.type.toUpperCase()} [{det.confidence.toFixed(2)}]</p>
                <p><span className="text-muted-text">Pipeline (%):</span> x:{det.bbox.x.toFixed(1)} y:{det.bbox.y.toFixed(1)} w:{det.bbox.width.toFixed(1)} h:{det.bbox.height.toFixed(1)}</p>
                <p><span className="text-muted-text">Render (px):</span> x:{Math.round((det.bbox.x / 100) * imageWidth)} y:{Math.round((det.bbox.y / 100) * imageHeight)} w:{Math.round((det.bbox.width / 100) * imageWidth)} h:{Math.round((det.bbox.height / 100) * imageHeight)}</p>
              </div>
            ))}
            {currentResult && currentResult.detections?.length > 3 && (
              <p className="text-muted-text mt-1 italic">+ {currentResult.detections.length - 3} more detections</p>
            )}
          </div>
        </div>
      )}

      {/* Hidden 1:1 Stage for Exporting */}
      <div style={{ position: 'absolute', top: -9999, left: -9999, opacity: 0, pointerEvents: 'none' }}>
        <Stage ref={exportStageRef} width={imageWidth} height={imageHeight}>
          <Layer>
            {image && <KonvaImage image={image} />}
            {layers.map((layer) => (
              <BlurEngine key={`export-${layer.id}`} layer={layer} image={image} />
            ))}
          </Layer>
        </Stage>
      </div>
    </div>
  );
}
