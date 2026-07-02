import { NextResponse } from 'next/server';

export const maxDuration = 60;

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const imageBase64 = body?.imageBase64 ?? '';
    const trustedFaceImages = body?.trustedFaceImages ?? [];

    if (!imageBase64 || typeof imageBase64 !== 'string') {
      return NextResponse.json({ error: 'imageBase64 is required' }, { status: 400 });
    }

    const rawBase64 = imageBase64.replace(/^data:image\/\w+;base64,/, '');

    const isProd = process.env.NODE_ENV === 'production';
    const defaultApiUrl = isProd ? 'https://sweet-shirts-sneeze.loca.lt' : 'http://127.0.0.1:8000';
    const apiUrl = process.env.PYTHON_API_URL || defaultApiUrl;
    
    const pythonReq = await fetch(`${apiUrl}/scan`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Bypass-Tunnel-Reminder': 'true'
      },
      body: JSON.stringify({
        imageBase64: `data:image/jpeg;base64,${rawBase64}`,
        trusted_faces_base64: trustedFaceImages,
      }),
      signal: AbortSignal.timeout(10000) // 10 seconds for submission should be plenty
    });
    
    if (pythonReq.ok) {
      const pyRes = await pythonReq.json();
      console.info(`[API/scan] Job queued successfully: ${pyRes.job_id}`);
      return NextResponse.json({ job_id: pyRes.job_id, status: pyRes.status });
    } else {
      const errorText = await pythonReq.text();
      console.error(`[API/scan] Python backend rejected request: ${pythonReq.status}. Body: ${errorText}`);
      return NextResponse.json({ error: 'Backend rejected the scan request', details: errorText }, { status: pythonReq.status });
    }
  } catch (err: any) {
    console.error('[API/scan] Failed to submit job:', err.message || err);
    return NextResponse.json({ error: 'Failed to contact AI backend', details: err.message }, { status: 500 });
  }
}
