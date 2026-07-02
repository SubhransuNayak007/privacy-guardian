import { NextResponse } from 'next/server';

export const maxDuration = 60;

export async function GET(req: Request, { params }: { params: Promise<{ jobId: string }> }) {
  try {
    const { jobId } = await params;
    if (!jobId) {
      return new Response('jobId is required', { status: 400 });
    }

    const isProd = process.env.NODE_ENV === 'production';
    const defaultApiUrl = isProd ? 'https://sweet-shirts-sneeze.loca.lt' : 'http://127.0.0.1:8000';
    const apiUrl = process.env.PYTHON_API_URL || defaultApiUrl;

    const pythonReq = await fetch(`${apiUrl}/image/${jobId}`, {
      method: 'GET',
      headers: {
        'Bypass-Tunnel-Reminder': 'true'
      }
    });

    if (!pythonReq.ok) {
      const text = await pythonReq.text();
      return new Response(`Failed to fetch image from Python: ${text}`, { status: pythonReq.status });
    }

    // Stream the image directly to the client
    return new Response(pythonReq.body, {
      status: 200,
      headers: {
        'Content-Type': 'image/jpeg',
        'Cache-Control': 'public, max-age=86400'
      }
    });
  } catch (err: any) {
    console.error('[API/image] Failed to fetch image:', err.message || err);
    return new Response(`Error: ${err.message}`, { status: 500 });
  }
}
