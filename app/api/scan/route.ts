import { ImageAnnotatorClient } from '@google-cloud/vision';
import { NextResponse } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import path from 'path';

// Initialize Google Cloud Vision client lazily (avoids module-load crash when
// GOOGLE_APPLICATION_CREDENTIALS is missing — it fails at call-time instead,
// allowing the Tesseract fallback to run).
let visionClient: ImageAnnotatorClient | null = null;
function getVisionClient(): ImageAnnotatorClient {
  if (!visionClient) {
    visionClient = new ImageAnnotatorClient();
  }
  return visionClient;
}

export async function POST(req: Request) {
  // ── 1. Parse body BEFORE the try block so it remains in scope for fallback ──
  let imageBase64 = '';
  let trustedFaceImages: string[] = [];
  let bodyError: string | null = null;

  try {
    const body = await req.json();
    imageBase64 = body?.imageBase64 ?? '';
    trustedFaceImages = body?.trustedFaceImages ?? [];
  } catch {
    bodyError = 'Invalid JSON body';
  }

  if (bodyError) {
    return NextResponse.json({ error: bodyError }, { status: 400 });
  }

  if (!imageBase64 || typeof imageBase64 !== 'string') {
    return NextResponse.json({ error: 'imageBase64 is required' }, { status: 400 });
  }

  // Strip data URI prefix once; reuse the raw base64 string everywhere
  const rawBase64 = imageBase64.replace(/^data:image\/\w+;base64,/, '');

  // ── 2. Auth check (non-blocking — we allow unauthenticated local dev) ──────
  try {
    const cookieStore = await cookies();
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        cookies: {
          getAll() { return cookieStore.getAll(); },
        },
      }
    );
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      console.warn('[API/scan] No auth session — running in local-dev mode.');
    }
  } catch {
    // Auth check failing must not prevent OCR
    console.warn('[API/scan] Auth check failed — continuing without user context.');
  }

  // ── 3. Attempt Python FastAPI Backend (V2 Architecture) ──────────────────
  try {
    console.info(`[API/scan] Attempting Python FastAPI backend at ${process.env.PYTHON_API_URL || 'http://127.0.0.1:8000'}/scan...`);
    
    // Convert base64 back to the format FastAPI expects (or just send raw)
    const pythonReq = await fetch(`${process.env.PYTHON_API_URL || 'http://127.0.0.1:8000'}/scan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        imageBase64: `data:image/jpeg;base64,${rawBase64}`,
        trusted_faces_base64: trustedFaceImages,
      }),
      // Longer timeout: GLiNER model downloads ~400 MB on first request, and OCR takes time on CPU
      signal: AbortSignal.timeout(300000)
    });
    
    if (pythonReq.ok) {
      const pyRes = await pythonReq.json();
      console.info(`[API/scan] Python backend succeeded — ${pyRes.detections?.length || 0} entities detected in ${pyRes.processingTime}ms.`);

      // V4: Python backend returns clean detections[] with bbox in 0–100%.
      // Map to frontend Detection shape (bbox uses x/y/width/height in 0–100%).
      const pythonDetections = (pyRes.detections || []).map((d: any) => {
        let x = 0, y = 0, w = 0, h = 0;
        if (Array.isArray(d.bbox)) {
          x = d.bbox[0] || 0;
          y = d.bbox[1] || 0;
          w = d.bbox[2] || 0;
          h = d.bbox[3] || 0;
        } else if (d.bbox) {
          x = d.bbox.x0 ?? d.bbox.x ?? 0;
          y = d.bbox.y0 ?? d.bbox.y ?? 0;
          w = d.bbox.width ?? (d.bbox.x1 ? d.bbox.x1 - x : 0);
          h = d.bbox.height ?? (d.bbox.y1 ? d.bbox.y1 - y : 0);
          x = d.bbox.x0 || 0;
          y = d.bbox.y0 || 0;
          w = (d.bbox.x1 || 0) - x;
          h = (d.bbox.y1 || 0) - y;
        }
        return {
          id:         d.id || `py-${Math.random().toString(36).slice(2, 9)}`,
          type:       d.type,
          label:      d.label,
          text:       d.text,
          confidence: d.confidence,
          bbox:       { x, y, width: w, height: h },
          redacted:   d.redacted ?? true
        };
      });

      // Python backend now handles ALL detection internally:
      // OCR+Regex+GLiNER (PII text), InsightFace (faces), NudeNet (body parts),
      // YOLOv8-weapons (guns/rifles), YOLOv8-smoking (cigarettes), YOLOv8-plates (license plates)
      // No external AI API needed.
      const allDetections = [...pythonDetections];

      // OCR words — already normalised to 0–100% by the V4 Python backend.
      const rawWords = (pyRes.words || []).map((w: any) => ({
        text:       w.text,
        confidence: w.confidence,
        bbox: {
          x0: w.bbox.x0,
          y0: w.bbox.y0,
          x1: w.bbox.x1,
          y1: w.bbox.y1,
        },
      }));

      const faceDetections = allDetections.filter((d: any) => d.type === 'face');
      const privacyScore = pyRes.privacyScore || 100;

      return NextResponse.json({
        fullText:          pyRes.fullText || '',
        words:             rawWords,
        pythonDetections:  allDetections,   // 🔥 V4: consumed by pipeline.ts directly
        confidence:        100,
        faces:             faceDetections.map((f: any) => ({ confidence: f.confidence, bbox: { x0: f.bbox.x, y0: f.bbox.y, x1: f.bbox.x + f.bbox.width, y1: f.bbox.y + f.bbox.height } })),
        labels:            [],
        privacyScore:      privacyScore,
        riskScore:         100 - privacyScore,
        riskLevel:         pyRes.riskLevel || 'Low',
        aiDescription:     pyRes.aiDescription || '',
      });

    } else {
      const errorText = await pythonReq.text();
      console.warn(`[API/scan] Python backend returned status ${pythonReq.status}. Body: ${errorText}`);
    }
  } catch (pyError: any) {
    console.warn('[API/scan] Python backend unreachable or failed. Falling back to GCV/Tesseract...', pyError.message);
  }

  // ── 4. Attempt Google Cloud Vision (Fallback) ─────────────────────────────
  try {
    if (!process.env.GOOGLE_APPLICATION_CREDENTIALS && !process.env.GOOGLE_CLOUD_PROJECT) {
      throw new Error(
        'Google Cloud Vision credentials are not configured. ' +
        'Set GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON) in .env.local.'
      );
    }

    const client = getVisionClient();
    const [result] = await client.annotateImage({
      image: { content: rawBase64 },
      features: [
        { type: 'DOCUMENT_TEXT_DETECTION' },
        { type: 'FACE_DETECTION' },
        { type: 'LABEL_DETECTION' },
        { type: 'SAFE_SEARCH_DETECTION' },
        { type: 'OBJECT_LOCALIZATION' },
      ],
    });

    // ── Face annotations ──
    const faces = (result.faceAnnotations || []).map(face => {
      const vertices = face.boundingPoly?.vertices || [];
      const xs = vertices.map(v => v.x || 0);
      const ys = vertices.map(v => v.y || 0);
      return {
        confidence: (face.detectionConfidence || 0) * 100,
        bbox: {
          x0: Math.min(...xs),
          y0: Math.min(...ys),
          x1: Math.max(...xs),
          y1: Math.max(...ys),
        },
      };
    });

    // ── Label annotations ──
    const labels = (result.labelAnnotations || []).map(l => ({
      description: l.description || '',
      score: (l.score || 0) * 100,
    }));

    const fullTextAnnotation = result.fullTextAnnotation;
    if (!fullTextAnnotation) {
      return NextResponse.json({ fullText: '', words: [], faces, labels, confidence: 0 });
    }

    // ── Word-level bboxes ──
    const words: any[] = [];
    let confidenceSum = 0;
    for (const page of fullTextAnnotation.pages || []) {
      for (const block of page.blocks || []) {
        for (const paragraph of block.paragraphs || []) {
          for (const word of paragraph.words || []) {
            const wordText = (word.symbols || []).map((s: any) => s.text).join('');
            const verts = word.boundingBox?.vertices || [];
            if (verts.length > 0) {
              const wxs = verts.map((v: any) => v.x || 0);
              const wys = verts.map((v: any) => v.y || 0);
              const conf = (word.confidence || 0) * 100;
              confidenceSum += conf;
              words.push({
                text: wordText,
                confidence: conf,
                bbox: {
                  x0: Math.min(...wxs),
                  y0: Math.min(...wys),
                  x1: Math.max(...wxs),
                  y1: Math.max(...wys),
                },
              });
            }
          }
        }
      }
    }

    // ── SafeSearch Detection ──────────────────────────────────────────────────
    const LIKELY_THRESHOLD = ['LIKELY', 'VERY_LIKELY'];
    const safeSearch = result.safeSearchAnnotation || {};
    const safetyDetections: any[] = [];

    if (
      LIKELY_THRESHOLD.includes(safeSearch.adult as string) ||
      LIKELY_THRESHOLD.includes(safeSearch.racy as string)
    ) {
      safetyDetections.push({
        id: `safety-nudity-${Date.now()}`,
        type: 'nudity',
        label: 'Private Body Parts',
        text: '[PRIVATE CONTENT]',
        confidence: safeSearch.adult === 'VERY_LIKELY' ? 95 : 80,
        bbox: { x: 0, y: 0, width: 100, height: 100 }, // full image
        redacted: true,
        severity: 'high',
      });
    }

    if (LIKELY_THRESHOLD.includes(safeSearch.violence as string)) {
      safetyDetections.push({
        id: `safety-violence-${Date.now()}`,
        type: 'illegal_item',
        label: 'Violent Content',
        text: '[VIOLENT CONTENT]',
        confidence: safeSearch.violence === 'VERY_LIKELY' ? 95 : 80,
        bbox: { x: 0, y: 0, width: 100, height: 100 },
        redacted: true,
        severity: 'high',
      });
    }

    // ── Object Localization (weapons, drugs, illegal items) ──────────────────
    const ILLEGAL_OBJECTS = [
      'gun', 'firearm', 'rifle', 'pistol', 'weapon', 'knife', 'sword', 'dagger',
      'cigarette', 'cigar', 'tobacco', 'beer', 'alcohol', 'wine', 'liquor', 'bottle',
      'syringe', 'drug', 'pill', 'bomb', 'explosive', 'grenade', 'ammunition',
    ];

    const localizedObjects = result.localizedObjectAnnotations || [];
    for (const obj of localizedObjects) {
      const name = (obj.name || '').toLowerCase();
      const isIllegal = ILLEGAL_OBJECTS.some(kw => name.includes(kw));
      if (!isIllegal) continue;

      const verts = obj.boundingPoly?.normalizedVertices || [];
      if (verts.length < 2) continue;

      const xs = verts.map((v: any) => (v.x || 0) * 100);
      const ys = verts.map((v: any) => (v.y || 0) * 100);
      safetyDetections.push({
        id: `safety-obj-${obj.name}-${Date.now()}`,
        type: 'illegal_item',
        label: `Illegal/Sensitive Item: ${obj.name}`,
        text: obj.name || '',
        confidence: Math.round((obj.score || 0.8) * 100),
        bbox: {
          x: Math.min(...xs),
          y: Math.min(...ys),
          width: Math.max(...xs) - Math.min(...xs),
          height: Math.max(...ys) - Math.min(...ys),
        },
        redacted: true,
        severity: 'high',
      });
    }

    return NextResponse.json({
      fullText: fullTextAnnotation.text || '',
      words,
      confidence: words.length > 0 ? Math.round(confidenceSum / words.length) : 0,
      faces,
      labels,
      safetyDetections,
    });

  } catch (visionError: any) {
    console.error('[API/scan] Google Cloud Vision failed:', visionError.message || visionError);

    // ── 5. Tesseract.js server-side fallback ─────────────────────────────────
    // imageBase64 is accessible here because it was declared BEFORE the try block.
    try {
      console.warn('[API/scan] Attempting Tesseract.js fallback...');

      const TesseractModule = await import('tesseract.js');
      const createWorker =
        (TesseractModule as any).createWorker ??
        (TesseractModule as any).default?.createWorker;

      if (typeof createWorker !== 'function') {
        throw new Error('tesseract.js createWorker not found — check package version.');
      }

      // Use the eng.traineddata bundled in the project root so Tesseract does
      // not need to download it from the internet.
      const langPath = process.cwd(); // eng.traineddata lives at project root

      const workerPath = path.join(process.cwd(), 'node_modules', 'tesseract.js', 'src', 'worker-script', 'node', 'index.js');
      const corePath = path.join(process.cwd(), 'node_modules', 'tesseract.js-core', 'tesseract-core.wasm.js');

      const worker = await createWorker('eng', 1, {
        langPath,
        workerPath,
        corePath,
        logger: () => {}, // Always provide a no-op function to avoid 'logger is not a function' TypeError
      });

      const buffer = Buffer.from(rawBase64, 'base64');
      const { data } = await worker.recognize(buffer);
      await worker.terminate();

      const words = (data.words || []).map((w: any) => ({
        text: w.text,
        confidence: w.confidence,
        bbox: {
          x0: w.bbox.x0,
          y0: w.bbox.y0,
          x1: w.bbox.x1,
          y1: w.bbox.y1,
        },
      }));

      console.info(`[API/scan] Tesseract fallback succeeded — ${words.length} words detected.`);

      return NextResponse.json({
        fullText: data.text || '',
        words,
        confidence: data.confidence || 0,
        faces: [],   // Tesseract doesn't detect faces
        labels: [],
      });

    } catch (tesseractError: any) {
      console.error('[API/scan] Tesseract fallback failed:', tesseractError.message || tesseractError);
      return NextResponse.json(
        {
          error:
            'OCR failed: Python Backend Unreachable, Google Cloud Vision failed, and Tesseract fallback also failed. ' +
            'Reason: ' + (tesseractError.message || 'unknown'),
          visionError: visionError.message,
          tesseractError: tesseractError.message,
        },
        { status: 500 }
      );
    }
  }
}
