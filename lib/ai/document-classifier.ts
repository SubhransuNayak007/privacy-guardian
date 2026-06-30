// lib/ai/document-classifier.ts

export type DocumentType = 
  | 'Aadhaar Card'
  | 'PAN Card'
  | 'Passport'
  | 'Driving Licence'
  | 'Voter ID'
  | 'Bank Statement'
  | 'Cheque'
  | 'Credit Card'
  | 'Invoice'
  | 'Screenshot'
  | 'Unknown Document';

/**
 * Robust document classification using OCR text and Google Vision Labels
 */
export function classifyDocument(fullText: string, labels: any[] = []): DocumentType {
  const text = fullText.toLowerCase().replace(/\s+/g, ' ');
  const labelNames = labels.map(l => l.description.toLowerCase());

  // Check OCR text first for high-confidence keywords
  if (text.includes('government of india') && text.includes('aadhaar')) {
    return 'Aadhaar Card';
  }
  if (text.includes('income tax department') || text.includes('permanent account number')) {
    return 'PAN Card';
  }
  if (text.includes('republic of india') && text.includes('passport')) {
    return 'Passport';
  }
  if (text.includes('driving licence') || text.includes('driver license')) {
    return 'Driving Licence';
  }
  if (text.includes('election commission of india')) {
    return 'Voter ID';
  }
  
  // Checking financial documents
  if (text.includes('bank') && (text.includes('statement') || text.includes('account summary'))) {
    return 'Bank Statement';
  }
  if (text.includes('pay') && text.includes('rupees') && text.includes('a/c no')) {
    return 'Cheque';
  }
  if (text.includes('invoice') || text.includes('bill to') || text.includes('tax invoice')) {
    return 'Invoice';
  }

  // Fallback to labels
  if (labelNames.includes('credit card') || text.includes('mastercard') || text.includes('visa')) {
    return 'Credit Card';
  }
  if (labelNames.includes('screenshot')) {
    return 'Screenshot';
  }
  if (labelNames.some(l => l.includes('passport'))) {
    return 'Passport';
  }
  if (labelNames.some(l => l.includes('id card') || l.includes('identity'))) {
    // If it's an ID card but we missed the exact text, default to Aadhaar if we see numbers in a row
    if (/\b\d{4}\s\d{4}\s\d{4}\b/.test(text)) return 'Aadhaar Card';
    return 'Unknown Document'; // Or a generic 'Identity Card'
  }

  return 'Unknown Document';
}
