import { GoogleGenerativeAI } from '@google/generative-ai';
import { NextResponse } from 'next/server';

// Lazy-init Gemini client so missing API key fails at call time, not load time
let genAI: GoogleGenerativeAI | null = null;
function getGenAI(): GoogleGenerativeAI {
  if (!genAI) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) throw new Error('GEMINI_API_KEY is not set in environment');
    genAI = new GoogleGenerativeAI(apiKey);
  }
  return genAI;
}

export interface DetectionForValidation {
  id: string;
  type: string;
  label: string;
  text: string;
}

export interface ValidationResult {
  id: string;
  keep: boolean;
  reason: string;
}

const SYSTEM_PROMPT = `You are a privacy and content moderation expert. 
You will be given the full OCR text extracted from a document image, and a list of detected items that a regex/ML system flagged as potentially sensitive.

Your task: For each detected item, determine if it is GENUINELY sensitive personal information in this specific context, or if it is a false positive (generic reference, public information, fictional example, table data, etc.).

Rules:
- A paper size table with numbers like "8.5 x 11" is NOT an address
- "U.S. Government" in a paper size reference is NOT a person's name
- Generic document templates with placeholder text are NOT real PII
- Public company names and product names are NOT personal information
- A phone number on a professional website in context of contact info IS sensitive
- A real person's home address IS sensitive
- Medical record numbers, SSNs, passport numbers ARE sensitive
- Standard reference codes in technical documents are NOT sensitive
- Measurements and sizes are NOT addresses or phone numbers

Return ONLY a valid JSON array (no markdown, no explanation):
[{"id":"<id>","keep":true,"reason":"<brief reason>"},...]

Be conservative - when genuinely unsure, keep the detection (keep: true).`;

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { fullText, detections } = body as {
      fullText: string;
      detections: DetectionForValidation[];
    };

    if (!fullText || !detections || detections.length === 0) {
      return NextResponse.json({ validated: [] });
    }

    // Try Gemini validation
    try {
      const ai = getGenAI();
      // gemini-2.0-flash is the latest fast model available on AI Studio
      const model = ai.getGenerativeModel({ model: 'gemini-1.5-flash' });

      const userMessage = `Full OCR text from document:
"""
${fullText.slice(0, 3000)}
"""

Detected items to validate:
${detections.map(d => `- id="${d.id}" type="${d.type}" label="${d.label}" text="${d.text}"`).join('\n')}

Return JSON array validating each item:`;

      const result = await model.generateContent([
        { text: SYSTEM_PROMPT },
        { text: userMessage },
      ]);

      const rawText = result.response.text().trim();
      // Strip any markdown code fences if present
      const jsonText = rawText.replace(/^```(?:json)?\n?/i, '').replace(/\n?```$/i, '').trim();
      const validated: ValidationResult[] = JSON.parse(jsonText);

      console.info(`[Validate] Gemini validated ${validated.length} detections. Kept: ${validated.filter(v => v.keep).length}`);

      return NextResponse.json({ validated, source: 'gemini' });

    } catch (geminiError: any) {
      console.warn('[Validate] Gemini validation failed, keeping all detections:', geminiError.message);
      // Fallback: keep all detections if Gemini fails
      const fallback: ValidationResult[] = detections.map(d => ({
        id: d.id,
        keep: true,
        reason: 'Gemini unavailable — keeping by default',
      }));
      return NextResponse.json({ validated: fallback, source: 'fallback' });
    }

  } catch (err: any) {
    console.error('[Validate] Request error:', err.message);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
