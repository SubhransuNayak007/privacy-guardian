import { GoogleGenerativeAI } from '@google/generative-ai';
import { NextResponse } from 'next/server';

export const maxDuration = 60;

let genAI: GoogleGenerativeAI | null = null;
function getGenAI(): GoogleGenerativeAI {
  if (!genAI) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) throw new Error('GEMINI_API_KEY is not set');
    genAI = new GoogleGenerativeAI(apiKey);
  }
  return genAI;
}

export interface VisionSafetyDetection {
  id: string;
  type: string;
  label: string;
  confidence: number;
  bbox: { x: number; y: number; width: number; height: number }; // 0–100 %
  redacted: boolean;
}

const SAFETY_PROMPT = `Analyze this image for safety-sensitive visual content that must be blurred for privacy and safety reasons.

Detect and locate:
1. WEAPONS: guns, rifles, pistols, shotguns, knives, machetes, bombs, grenades, tasers
2. TOBACCO/SMOKING: cigarettes, cigars, vapes, e-cigarettes, joints/cannabis
3. ILLEGAL DRUGS: syringes with drugs, drug paraphernalia, pills/tablets on table, powder drugs
4. NUDITY/EXPLICIT: exposed genitalia, bare breasts (female), bare buttocks, explicit sexual content
5. ALCOHOL: alcohol bottles (beer, wine, spirits), shot glasses with liquid, open alcohol cans

For EACH detected item, provide a bounding box. Use coordinates from 0 to 1000 (1000 = full image dimension).

Return ONLY a valid JSON array. No markdown, no explanation:
[
  {
    "type": "weapon|tobacco|drug|nudity|alcohol",
    "label": "specific item name e.g. Rifle, Cigarette, Female Breast, Whiskey Bottle",
    "ymin": 0-1000,
    "xmin": 0-1000,
    "ymax": 0-1000,
    "xmax": 0-1000,
    "confidence": 0-100
  }
]

If nothing safety-sensitive is found, return: []
Be thorough — detect ALL instances of each category.`;

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { imageBase64 } = body as { imageBase64: string };

    if (!imageBase64) {
      return NextResponse.json({ detections: [] });
    }

    // Strip data URI prefix and get mime type
    let mimeType: 'image/jpeg' | 'image/png' | 'image/webp' = 'image/jpeg';
    let rawBase64 = imageBase64;
    const match = imageBase64.match(/^data:(image\/\w+);base64,(.+)$/);
    if (match) {
      mimeType = match[1] as any;
      rawBase64 = match[2];
    } else {
      rawBase64 = imageBase64.replace(/^data:image\/\w+;base64,/, '');
    }

    try {
      const ai = getGenAI();
      const model = ai.getGenerativeModel({ model: 'gemini-1.5-flash' });

      const result = await model.generateContent([
        {
          inlineData: {
            mimeType,
            data: rawBase64,
          },
        },
        { text: SAFETY_PROMPT },
      ], { requestOptions: { timeout: 8000 } });

      const rawText = result.response.text().trim();
      // Strip markdown fences
      const jsonText = rawText
        .replace(/^```(?:json)?\n?/i, '')
        .replace(/\n?```$/i, '')
        .trim();

      const parsed: any[] = JSON.parse(jsonText);

      const detections: VisionSafetyDetection[] = parsed.map((item: any) => {
        // Convert from 0-1000 Gemini coords to 0-100% for frontend
        const x = Math.max(0, Math.min(100, (item.xmin / 1000) * 100));
        const y = Math.max(0, Math.min(100, (item.ymin / 1000) * 100));
        const w = Math.max(1, Math.min(100 - x, ((item.xmax - item.xmin) / 1000) * 100));
        const h = Math.max(1, Math.min(100 - y, ((item.ymax - item.ymin) / 1000) * 100));

        return {
          id: `vision-${Math.random().toString(36).slice(2, 9)}`,
          type: item.type || 'illegal_item',
          label: item.label || 'Unsafe Content',
          confidence: Number(item.confidence) || 80,
          bbox: { x, y, width: w, height: h },
          redacted: true,
        };
      });

      console.info(`[VisionSafety] Gemini detected ${detections.length} safety item(s):`, detections.map(d => d.label));

      return NextResponse.json({ detections, source: 'gemini-vision' });

    } catch (err: any) {
      console.warn('[VisionSafety] Gemini vision scan failed:', err.message);
      return NextResponse.json({ detections: [], error: err.message });
    }

  } catch (err: any) {
    console.error('[VisionSafety] Request error:', err.message);
    return NextResponse.json({ detections: [], error: err.message }, { status: 500 });
  }
}
