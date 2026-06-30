export interface OCRWord {
  text: string;
  confidence: number;
  bbox: { x0: number; y0: number; x1: number; y1: number };
}

export interface OCRResult {
  fullText: string;
  words: OCRWord[];
  confidence: number; // average across all words
  faces?: any[];
  labels?: any[];
  diagnostics?: Record<string, string>;
}

export type OCRProgressCallback = (progress: number, status: string) => void;

/**
 * Runs Google Cloud Vision OCR by calling our API route.
 * Reports progress via optional callback.
 */
export async function runOCR(
  imageFile: File | Blob,
  trustedFaceImages?: string[],
  onProgress?: OCRProgressCallback
): Promise<OCRResult> {
  if (onProgress) {
    onProgress(10, 'Preparing image for analysis...');
  }

  // Convert File/Blob to Base64
  const base64 = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error('Failed to read file as Base64'));
    reader.readAsDataURL(imageFile);
  });

  if (onProgress) {
    onProgress(30, 'Analyzing document text...');
  }

  try {
    // Call our Next.js API route
    const response = await fetch('/api/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        imageBase64: base64,
        trustedFaceImages: trustedFaceImages || []
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      if (response.status === 401) {
        throw new Error('Unauthorized access. Please log in.');
      }
      throw new Error(errorData.error || `Failed to process document (Status: ${response.status})`);
    }

    const result: OCRResult = await response.json();

    // Allow empty text for images with no text (e.g., face only)
    if (!result.fullText) {
      result.fullText = '';
    }

    if (onProgress) {
      onProgress(100, 'Text analysis complete');
    }

    return result;
  } catch (error: any) {
    // If the server API failed (including server-side Tesseract fallback), just throw
    // Do not attempt client-side OCR as it is often blocked by CSP/Adblockers
    console.error('Vision API request failed:', error.message || error);
    throw new Error(error.message || 'OCR failed. Detection cannot continue.');
  }
}

/**
 * Finds the pixel bounding boxes for matched text within OCR word list.
 * Returns normalized bbox (0-1) relative to image dimensions.
 */
export function findWordBBoxes(
  matchedText: string,
  words: OCRWord[],
  imageWidth: number,
  imageHeight: number
): Array<{ x: number; y: number; width: number; height: number }> {
  const bboxes: Array<{ x: number; y: number; width: number; height: number }> = [];
  const matchClean = matchedText.toLowerCase().replace(/[^a-z0-9]/gi, '');
  if (!matchClean) return bboxes;

  const pad = 0.01; // 1% padding to ensure we don't clip edges

  // 1. Sliding Window Search (For perfect sequential matches)
  for (let i = 0; i < words.length; i++) {
    let combined = '';
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    
    for (let j = i; j < Math.min(words.length, i + 20); j++) {
      const wClean = words[j].text.toLowerCase().replace(/[^a-z0-9]/gi, '');
      combined += wClean;
      
      minX = Math.min(minX, words[j].bbox.x0);
      minY = Math.min(minY, words[j].bbox.y0);
      maxX = Math.max(maxX, words[j].bbox.x1);
      maxY = Math.max(maxY, words[j].bbox.y1);
      
      if (combined.includes(matchClean)) {
        bboxes.push({
          x: Math.max(0, ((minX / imageWidth) - pad) * 100),
          y: Math.max(0, ((minY / imageHeight) - pad) * 100),
          width: Math.min(100, (((maxX - minX) / imageWidth) + (pad * 2)) * 100),
          height: Math.min(100, (((maxY - minY) / imageHeight) + (pad * 2)) * 100),
        });
        return bboxes; // Found perfect sequence!
      }
    }
  }

  // 2. Fallback: Spatial Anchor Clustering (For fragmented/disordered OCR blocks)
  const tokens = matchedText.toLowerCase().replace(/[^a-z0-9\s]/gi, ' ').split(/\s+/).filter(t => t.length > 2);
  if (tokens.length > 0) {
    let anchor: OCRWord | null = null;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    let foundTokens = 0;
    
    for (const word of words) {
      const wClean = word.text.toLowerCase().replace(/[^a-z0-9]/gi, '');
      if (wClean.length < 2) continue;
      
      let matched = false;
      for (const token of tokens) {
        if (token.includes(wClean) || wClean.includes(token)) {
          matched = true; break;
        }
      }
      
      if (matched) {
        if (!anchor) {
          anchor = word;
          minX = word.bbox.x0; minY = word.bbox.y0; 
          maxX = word.bbox.x1; maxY = word.bbox.y1;
          foundTokens++;
        } else {
          // Check spatial proximity to anchor (within 30% of image dimensions)
          const dist = Math.sqrt(Math.pow(word.bbox.x0 - anchor.bbox.x0, 2) + Math.pow(word.bbox.y0 - anchor.bbox.y0, 2));
          if (dist < Math.max(imageWidth, imageHeight) * 0.3) {
            minX = Math.min(minX, word.bbox.x0);
            minY = Math.min(minY, word.bbox.y0);
            maxX = Math.max(maxX, word.bbox.x1);
            maxY = Math.max(maxY, word.bbox.y1);
            foundTokens++;
          }
        }
      }
    }
    
    if (foundTokens >= Math.max(1, tokens.length / 2) && minX !== Infinity) {
      bboxes.push({
        x: Math.max(0, ((minX / imageWidth) - pad) * 100),
        y: Math.max(0, ((minY / imageHeight) - pad) * 100),
        width: Math.min(100, (((maxX - minX) / imageWidth) + (pad * 2)) * 100),
        height: Math.min(100, (((maxY - minY) / imageHeight) + (pad * 2)) * 100),
      });
    }
  }

  return bboxes;
}
