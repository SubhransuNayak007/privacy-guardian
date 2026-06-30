import { FaceDetector, FilesetResolver } from '@mediapipe/tasks-vision';

let faceDetector: FaceDetector | null = null;
let isInitializing = false;
let initPromise: Promise<FaceDetector> | null = null;

// Initialize the MediaPipe Face Detector
async function initFaceDetector(): Promise<FaceDetector> {
  if (faceDetector) return faceDetector;
  
  if (isInitializing && initPromise) {
    return initPromise;
  }
  
  isInitializing = true;
  initPromise = new Promise(async (resolve, reject) => {
    try {
      const vision = await FilesetResolver.forVisionTasks(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.3/wasm"
      );
      
      const originalConsoleError = console.error;
      console.error = (...args) => {
        if (typeof args[0] === 'string' && args[0].includes('Created TensorFlow Lite XNNPACK delegate for CPU')) {
          return;
        }
        originalConsoleError(...args);
      };

      faceDetector = await FaceDetector.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite",
          delegate: "CPU" // Use CPU delegate to avoid WebGL crashes on some devices
        },
        runningMode: "IMAGE",
        minDetectionConfidence: 0.3, // Lower confidence to catch more faces, especially smaller ones
      });
      
      console.error = originalConsoleError;
      
      resolve(faceDetector);
    } catch (error) {
      console.error("Failed to initialize FaceDetector:", error);
      reject(error);
    } finally {
      isInitializing = false;
    }
  });
  
  return initPromise;
}

export interface BBox {
  x: number; // Normalized 0-1
  y: number; // Normalized 0-1
  width: number; // Normalized 0-1
  height: number; // Normalized 0-1
  confidence: number;
}

/**
 * Resizes the image to a target width while keeping aspect ratio, returns an HTMLCanvasElement
 */
async function getScaledCanvas(blob: Blob, targetWidth: number): Promise<HTMLCanvasElement | null> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(blob);
    const img = new Image();
    img.onload = () => {
      const scale = targetWidth / img.width;
      const targetHeight = img.height * scale;
      
      const canvas = document.createElement('canvas');
      canvas.width = targetWidth;
      canvas.height = targetHeight;
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        URL.revokeObjectURL(url);
        resolve(null);
        return;
      }
      
      ctx.drawImage(img, 0, 0, targetWidth, targetHeight);
      resolve(canvas);
      URL.revokeObjectURL(url);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      resolve(null);
    };
    img.src = url;
  });
}

/**
 * Calculates IoU (Intersection over Union) for deduplication
 */
function calculateIoU(box1: BBox, box2: BBox): number {
  const xA = Math.max(box1.x, box2.x);
  const yA = Math.max(box1.y, box2.y);
  const xB = Math.min(box1.x + box1.width, box2.x + box2.width);
  const yB = Math.min(box1.y + box1.height, box2.y + box2.height);

  const interArea = Math.max(0, xB - xA) * Math.max(0, yB - yA);
  const box1Area = box1.width * box1.height;
  const box2Area = box2.width * box2.height;

  return interArea / (box1Area + box2Area - interArea);
}

/**
 * Runs single-stage face detection using HTMLImageElement
 */
export async function detectFacesMultiStage(imageBlob: Blob): Promise<BBox[]> {
  try {
    const detector = await initFaceDetector();
    
    // Load original image to get dimensions
    const url = URL.createObjectURL(imageBlob);
    const img = new Image();
    
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error("Failed to load image for face detection"));
      img.src = url;
    });

    const origWidth = img.width;
    const origHeight = img.height;
    
    // Resize for detection to avoid WASM memory limits on huge images
    const MAX_DIM = 1280;
    let targetW = img.width;
    let targetH = img.height;
    
    if (img.width > MAX_DIM || img.height > MAX_DIM) {
      if (img.width > img.height) {
        targetW = MAX_DIM;
        targetH = Math.round((img.height / img.width) * MAX_DIM);
      } else {
        targetH = MAX_DIM;
        targetW = Math.round((img.width / img.height) * MAX_DIM);
      }
    }

    try {
      const canvas = document.createElement('canvas');
      canvas.width = targetW;
      canvas.height = targetH;
      const ctx = canvas.getContext('2d');
      if (!ctx) throw new Error("Could not get 2d context");
      ctx.drawImage(img, 0, 0, targetW, targetH);
      
      const imageData = ctx.getImageData(0, 0, targetW, targetH);

      // Intercept console.error to suppress MediaPipe's harmless INFO logs that trigger Next.js error overlays
      const originalConsoleError = console.error;
      console.error = (...args) => {
        if (typeof args[0] === 'string' && args[0].includes('Created TensorFlow Lite XNNPACK delegate for CPU')) {
          return; // Ignore this specific C++ stdout message mapped to stderr
        }
        originalConsoleError(...args);
      };

      const result = detector.detect(imageData);
      
      // Restore console.error
      console.error = originalConsoleError;

      const allDetections: BBox[] = [];

      for (const det of result.detections) {
        if (det.boundingBox) {
          // Convert from target canvas coordinates to normalized 0-1 coordinates
          const box = {
            x: det.boundingBox.originX / targetW,
            y: det.boundingBox.originY / targetH,
            width: det.boundingBox.width / targetW,
            height: det.boundingBox.height / targetH,
            confidence: det.categories[0]?.score || 0
          };

          // BlazeFace returns a very tight box around facial features.
          // Expand it slightly by 5% to cover the edges of the face, but NOT the hair.
          const expandX = box.width * 0.05;
          const expandY = box.height * 0.05;
          
          const newX = Math.max(0, box.x - (expandX / 2));
          const newY = Math.max(0, box.y - (expandY / 2));
          
          allDetections.push({
            x: newX,
            y: newY,
            width: Math.min(1 - newX, box.width + expandX),
            height: Math.min(1 - newY, box.height + expandY),
            confidence: box.confidence
          });
        }
      }

      URL.revokeObjectURL(url);
      return allDetections;
    } catch (e) {
      console.error("Detector detect() crashed:", e);
      URL.revokeObjectURL(url);
      return [];
    }

  } catch (error) {
    console.error("Face detection error:", error);
    return [];
  }
}
