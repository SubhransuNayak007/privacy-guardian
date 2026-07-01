import { NextResponse } from 'next/server';

export const maxDuration = 60;

export async function GET(req: Request, { params }: { params: Promise<{ jobId: string }> }) {
  try {
    const { jobId } = await params;
    if (!jobId) {
      return NextResponse.json({ error: 'jobId is required' }, { status: 400 });
    }

    const pythonReq = await fetch(`${process.env.PYTHON_API_URL || 'http://127.0.0.1:8000'}/result/${jobId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Bypass-Tunnel-Reminder': 'true'
      }
    });

    if (pythonReq.status === 404) {
      return NextResponse.json({ status: 'not_found' }, { status: 404 });
    }

    if (pythonReq.ok) {
      const pyRes = await pythonReq.json();
      
      if (pyRes.status !== 'completed') {
        return NextResponse.json({ status: pyRes.status });
      }

      const resultObj = pyRes.result || pyRes;
      
      // Map Python detections to frontend format
      const pythonDetections = (resultObj.detections || []).map((d: any) => {
        let x = 0, y = 0, w = 0, h = 0;
        const boxObj = d.bbox || d.box;
        if (Array.isArray(boxObj)) {
          x = boxObj[0] || 0;
          y = boxObj[1] || 0;
          // In python pipeline, box is [x1, y1, x2, y2]
          w = (boxObj[2] || 0) - x;
          h = (boxObj[3] || 0) - y;
        } else if (boxObj) {
          x = boxObj.x0 ?? boxObj.x ?? 0;
          y = boxObj.y0 ?? boxObj.y ?? 0;
          w = boxObj.width ?? (boxObj.x1 ? boxObj.x1 - x : 0);
          h = boxObj.height ?? (boxObj.y1 ? boxObj.y1 - y : 0);
        }
        return {
          id:         d.id || `py-${Math.random().toString(36).slice(2, 9)}`,
          type:       d.type || d.label,
          label:      d.label,
          text:       d.text,
          confidence: (d.confidence ?? d.score ?? 0) * (d.score && d.score <= 1 ? 100 : 1),
          bbox:       { x, y, width: w, height: h },
          redacted:   d.redacted ?? true
        };
      });

      const rawWords = (resultObj.words || []).map((w: any) => ({
        text:       w.text,
        confidence: w.confidence,
        bbox: {
          x0: w.bbox.x0,
          y0: w.bbox.y0,
          x1: w.bbox.x1,
          y1: w.bbox.y1,
        },
      }));

      const faceDetections = pythonDetections.filter((d: any) => d.type === 'face');
      const privacyScore = resultObj.privacyScore || 100;

      return NextResponse.json({
        status: 'completed',
        fullText: resultObj.fullText || '',
        words: rawWords,
        pythonDetections,
        confidence: 100,
        faces: faceDetections.map((f: any) => ({ confidence: f.confidence, bbox: { x0: f.bbox.x, y0: f.bbox.y, x1: f.bbox.x + f.bbox.width, y1: f.bbox.y + f.bbox.height } })),
        labels: [],
        privacyScore,
        riskScore: 100 - privacyScore,
        riskLevel: resultObj.riskLevel || 'Low',
        aiDescription: resultObj.aiDescription || '',
        redactedImageBase64: resultObj.image || resultObj.redacted_image // python backend returned this
      });
    } else {
      const errorText = await pythonReq.text();
      console.error(`[API/result] Python backend rejected request: ${pythonReq.status}. Body: ${errorText}`);
      return NextResponse.json({ error: 'Backend rejected the result request', details: errorText }, { status: pythonReq.status });
    }
  } catch (err: any) {
    console.error('[API/result] Failed to fetch result:', err.message || err);
    return NextResponse.json({ error: 'Failed to contact AI backend', details: err.message }, { status: 500 });
  }
}
