// lib/ai/pii-patterns.ts
// Real PII detection regex patterns — applied to actual OCR text
// All patterns produce confidence bands based on match quality

export interface PIIMatch {
  type: string;
  label: string;
  maskedText: string;
  rawText: string;
  confidence: number; // 65–99 — never exactly 100
  startIndex: number;
  endIndex: number;
}

// ── Luhn algorithm for credit card validation ─────────────────────
function luhnCheck(num: string): boolean {
  const digits = num.replace(/\D/g, '').split('').map(Number);
  let sum = 0;
  let isEven = false;
  for (let i = digits.length - 1; i >= 0; i--) {
    let digit = digits[i];
    if (isEven) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    sum += digit;
    isEven = !isEven;
  }
  return sum % 10 === 0;
}

// ── Aadhaar checksum (Verhoeff) ───────────────────────────────────
const verhoeffMult = [
  [0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],
  [2,3,4,0,1,7,8,9,5,6],[3,4,0,1,2,8,9,5,6,7],
  [4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],
  [6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],
  [8,7,6,5,9,3,2,1,0,4],[9,8,7,6,5,4,3,2,1,0],
];
const verhoeffPerm = [
  [0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],
  [5,8,0,3,7,9,6,1,4,2],[8,9,1,6,0,4,3,5,2,7],
  [9,4,5,3,1,2,6,8,7,0],
];
function verhoeffValidate(num: string): boolean {
  const digits = num.replace(/\s/g, '').split('').reverse().map(Number);
  let c = 0;
  for (let i = 0; i < digits.length; i++) {
    c = verhoeffMult[c][verhoeffPerm[i % 5][digits[i]]];
  }
  return c === 0;
}

// ── PAN card format validation ─────────────────────────────────────
function isPanValid(pan: string): boolean {
  return /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(pan.toUpperCase());
}

// ── Mask helpers ───────────────────────────────────────────────────
function maskPhone(phone: string): string {
  const digits = phone.replace(/\D/g, '');
  if (digits.length >= 10) {
    return phone.replace(digits.slice(2, digits.length - 2), 'X'.repeat(digits.length - 4));
  }
  return phone.slice(0, 3) + 'XXXXX' + phone.slice(-2);
}

function maskEmail(email: string): string {
  const [local, domain] = email.split('@');
  if (!domain) return email.slice(0, 3) + '***';
  const maskedLocal = local.slice(0, 2) + '***';
  const domainParts = domain.split('.');
  return `${maskedLocal}@${domainParts[0].slice(0,2)}***.${domainParts.slice(-1)}`;
}

function maskAadhaar(aadhaar: string): string {
  const digits = aadhaar.replace(/\D/g, '');
  return `XXXX XXXX ${digits.slice(-4)}`;
}

function maskPAN(pan: string): string {
  return pan.slice(0, 2) + '***' + pan.slice(-2);
}

function maskCard(card: string): string {
  const digits = card.replace(/\D/g, '');
  return 'XXXX XXXX XXXX ' + digits.slice(-4);
}

function maskBank(account: string): string {
  const digits = account.replace(/\D/g, '');
  return 'XXXXXX' + digits.slice(-4);
}

// ── Main PII scanner ───────────────────────────────────────────────
export function scanForPII(text: string): PIIMatch[] {
  const results: PIIMatch[] = [];
  const seen = new Set<string>(); // deduplicate by matched text

  function addMatch(match: RegExpExecArray, config: {
    type: string;
    label: string;
    mask: (s: string) => string;
    baseConfidence: number;
    validate?: (s: string) => boolean;
    confidenceBonus?: number;
  }) {
    const rawText = match[0].trim();
    if (seen.has(rawText)) return;
    seen.add(rawText);

    const isValid = config.validate ? config.validate(rawText) : true;
    const confidence = Math.min(99,
      config.baseConfidence + (isValid ? (config.confidenceBonus ?? 5) : 0)
    );

    results.push({
      type: config.type,
      label: config.label,
      maskedText: config.mask(rawText),
      rawText,
      confidence: Math.round(confidence * 10) / 10,
      startIndex: match.index,
      endIndex: match.index + match[0].length,
    });
  }

  // ── Global Phone Numbers ──────────────────────────────────────────
  const phoneRe = /\b(?:(?:\+|00)\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b/g;
  let m: RegExpExecArray | null;
  while ((m = phoneRe.exec(text)) !== null) {
    addMatch(m, { type: 'phone', label: 'Phone Number', mask: maskPhone, baseConfidence: 88 });
  }

  // ── Email addresses ───────────────────────────────────────────
  const emailRe = /[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}/g;
  while ((m = emailRe.exec(text)) !== null) {
    addMatch(m, { type: 'email', label: 'Email Address', mask: maskEmail, baseConfidence: 92 });
  }

  // ── Aadhaar number ────────────────────────────────────────────
  const aadhaarRe = /\b\d{4}\s?\d{4}\s?\d{4}\b/g;
  while ((m = aadhaarRe.exec(text)) !== null) {
    const digits = m[0].replace(/\s/g, '');
    if (digits.length === 12 && !digits.startsWith('0') && !digits.startsWith('1')) {
      const isValid = verhoeffValidate(digits);
      addMatch(m, {
        type: 'aadhaar', label: 'Aadhaar Number',
        mask: maskAadhaar, baseConfidence: 85, validate: () => isValid, confidenceBonus: 10,
      });
    }
  }

  // ── PAN card ──────────────────────────────────────────────────
  const panRe = /\b[A-Z]{5}[0-9]{4}[A-Z]\b/g;
  while ((m = panRe.exec(text)) !== null) {
    addMatch(m, { type: 'pan', label: 'PAN Card', mask: maskPAN, baseConfidence: 90, validate: isPanValid, confidenceBonus: 8 });
  }

  // ── Credit/Debit Card (Luhn-validated) ───────────────────────
  const cardRe = /\b(?:\d[ -]?){15,16}\b/g;
  while ((m = cardRe.exec(text)) !== null) {
    const digits = m[0].replace(/\D/g, '');
    if ((digits.length === 15 || digits.length === 16) && luhnCheck(digits)) {
      addMatch(m, { type: 'credit_card', label: 'Credit/Debit Card', mask: maskCard, baseConfidence: 87, validate: luhnCheck, confidenceBonus: 10 });
    }
  }

  // ── Bank Account Numbers (10–18 digits, not already matched) ─
  const bankRe = /\b\d{9,18}\b/g;
  while ((m = bankRe.exec(text)) !== null) {
    const digits = m[0];
    // Skip if already matched as Aadhaar or card
    const alreadyMatched = results.some(r =>
      r.startIndex <= m!.index && r.endIndex >= m!.index + m![0].length
    );
    if (!alreadyMatched && digits.length >= 10 && digits.length <= 18) {
      addMatch(m, { type: 'bank_account', label: 'Bank Account', mask: maskBank, baseConfidence: 72 });
    }
  }

  // ── IFSC Code (bank identifier) ───────────────────────────────
  const ifscRe = /\b[A-Z]{4}0[A-Z0-9]{6}\b/g;
  while ((m = ifscRe.exec(text)) !== null) {
    addMatch(m, {
      type: 'bank_account', label: 'IFSC / Bank Code',
      mask: (s) => s.slice(0, 4) + 'XXXXXX', baseConfidence: 91,
    });
  }

  // ── Passport Number (Indian) ──────────────────────────────────
  const passportRe = /\b[A-Z][0-9]{7}\b/g;
  while ((m = passportRe.exec(text)) !== null) {
    addMatch(m, {
      type: 'pan', label: 'Passport Number',
      mask: (s) => s[0] + 'XXXXXX' + s.slice(-1), baseConfidence: 79,
    });
  }

  // ── Voter ID (India: 3 letters + 7 digits) ───────────────────────
  const voterRe = /\b[A-Z]{3}[0-9]{7}\b/g;
  while ((m = voterRe.exec(text)) !== null) {
    addMatch(m, {
      type: 'aadhaar', label: 'Voter ID',
      mask: (s) => s.slice(0, 3) + 'XXXXXXX', baseConfidence: 80,
    });
  }

  // ── Address clues (basic NER heuristic) ────────────────────────
  const addressRe = /(?:\b(?:House|Flat|No|Plot|Door|Shop|Block|At\/Po|Po|Vill|Village|Dist|District|Mandal|Taluka|Pin|State)\.?\s*[A-Za-z0-9/-]+\s*,?\s*)?(?:\b\d{1,5}[A-Za-z]?\s*,?\s*)?(?:[A-Za-z0-9., -]{3,30})\b(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Boulevard|Blvd|Drive|Dr|Nagar|Vihar|Colony|Sector|Phase|Marg|Puram|Ganj|Dist|District|Mandal|Taluka|State|Pin)\b/gi;
  while ((m = addressRe.exec(text)) !== null) {
    // Basic validation to avoid matching simple sentences
    if (m[0].length > 8) {
      addMatch(m, {
        type: 'address', label: 'Address',
        mask: (s) => s.split(',')[0] + ', [REDACTED]', baseConfidence: 78,
      });
    }
  }

  // ── PIN Code (6 digits, likely address context) ───────────────
  const pinRe = /\b[1-9][0-9]{5}\b/g;
  while ((m = pinRe.exec(text)) !== null) {
    const near = text.slice(Math.max(0, m.index - 30), m.index + 10).toLowerCase();
    if (/pin|postal|zip|code/.test(near)) {
      addMatch(m, { type: 'address', label: 'PIN Code', mask: (s) => s.slice(0, 2) + 'XXXX', baseConfidence: 76 });
    }
  }

  // ── Password patterns ─────────────────────────────────────────
  const passwordRe = /(?:password|pwd|passwd|secret|key)\s*[:=]\s*\S+/gi;
  while ((m = passwordRe.exec(text)) !== null) {
    addMatch(m, {
      type: 'password', label: 'Password / Credential',
      mask: (s) => s.replace(/[:=]\s*\S+/, ': [REDACTED]'), baseConfidence: 82,
    });
  }

  // ── UPI ID ────────────────────────────────────────────────────
  const upiRe = /\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b/g;
  while ((m = upiRe.exec(text)) !== null) {
    // Skip if it looks like an email
    if (!emailRe.test(m[0])) {
      addMatch(m, { type: 'bank_account', label: 'UPI ID', mask: (s) => s.split('@')[0].slice(0, 3) + '***@' + s.split('@')[1], baseConfidence: 85 });
    }
  }

  // ── Date of Birth (DOB / Year of Birth) ────────────────────────
  const dobRe = /(?:DOB|Date of Birth|YOB|Year of Birth)[\s:]*([0-9]{2}[\/\-][0-9]{2}[\/\-][0-9]{4}|[0-9]{4})/gi;
  while ((m = dobRe.exec(text)) !== null) {
    addMatch(m, { type: 'dob', label: 'Date of Birth', mask: () => '[REDACTED]', baseConfidence: 88 });
  }

  // ── Signature Heuristic ───────────────────────────────────────
  const sigRe = /(?:Signature|Sign)[\s:]/gi;
  while ((m = sigRe.exec(text)) !== null) {
    // We match the keyword, the actual signature image is redacted via bounding box merging if near
    addMatch(m, { type: 'signature', label: 'Signature Region', mask: () => '[REDACTED]', baseConfidence: 70 });
  }

  // ── Name Heuristic (Common Indian prefixes / Father's Name) ───
  const nameRe = /(?:Name|Father|Husband|S\/O|W\/O|D\/O)[\s:]+([A-Z][a-zA-Z\s]+)/g;
  while ((m = nameRe.exec(text)) !== null) {
    addMatch(m, { type: 'name', label: 'Name', mask: () => '[REDACTED]', baseConfidence: 75 });
  }

  // ── Wi-Fi Credentials ────────────────────────────────────────────
  const wifiRe = /(?:wifi|wi-fi|ssid|network|password|pwd|passphrase)\s*[:=]\s*\S+/gi;
  while ((m = wifiRe.exec(text)) !== null) {
    addMatch(m, {
      type: 'password', label: 'Wi-Fi Credential',
      mask: (s) => s.replace(/[:=]\s*\S+/, ': [REDACTED]'), baseConfidence: 88,
    });
  }

  // ── IP Address ──────────────────────────────────────────────────
  const ipRe = /\b(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b/g;
  while ((m = ipRe.exec(text)) !== null) {
    // Skip obviously non-private IPs (127.0.0.1, 0.0.0.0)
    if (m[0] !== '127.0.0.1' && m[0] !== '0.0.0.0') {
      addMatch(m, {
        type: 'address', label: 'IP Address',
        mask: (s) => s.replace(/\.\d+$/, '.***'), baseConfidence: 75,
      });
    }
  }

  // ── OTP / 2FA Code (6 digits near auth context) ─────────────────
  const otpRe = /\b\d{6}\b/g;
  while ((m = otpRe.exec(text)) !== null) {
    const ctx = text.slice(Math.max(0, m.index - 40), m.index + 10).toLowerCase();
    if (/otp|one.?time|2fa|authenticat|verify|code|token/.test(ctx)) {
      addMatch(m, {
        type: 'password', label: 'OTP / 2FA Code',
        mask: () => '******', baseConfidence: 90,
      });
    }
  }

  // ── VIN Number (17 alphanumeric, no I/O/Q) ───────────────────────
  const vinRe = /\b[A-HJ-NPR-Z0-9]{17}\b/g;
  while ((m = vinRe.exec(text)) !== null) {
    addMatch(m, {
      type: 'address', label: 'VIN Number',
      mask: (s) => s.slice(0, 3) + '**********' + s.slice(-4), baseConfidence: 82,
    });
  }

  // ── Crypto Private Key / Seed Phrase ────────────────────────────
  // 64-char hex (private key)
  const hexKeyRe = /\b[0-9a-fA-F]{64}\b/g;
  while ((m = hexKeyRe.exec(text)) !== null) {
    addMatch(m, {
      type: 'password', label: 'Crypto Private Key',
      mask: (s) => s.slice(0, 8) + '...[REDACTED]', baseConfidence: 95,
    });
  }

  // ── API Key / Secret Token ──────────────────────────────────────
  const apiKeyRe = /(?:api.?key|api.?secret|access.?token|secret.?key|bearer)\s*[:=]\s*['"]?([A-Za-z0-9\-_.~+/]{20,})/gi;
  while ((m = apiKeyRe.exec(text)) !== null) {
    addMatch(m, {
      type: 'password', label: 'API Key / Secret',
      mask: (s) => s.replace(/[:=]\s*['"]?[A-Za-z0-9\-_.~+/]{20,}/, ': [REDACTED]'), baseConfidence: 92,
    });
  }

  return results.sort((a, b) => b.confidence - a.confidence);
}


