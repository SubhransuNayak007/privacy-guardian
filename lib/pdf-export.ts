// lib/pdf-export.ts
// Client-side PDF report generation using jsPDF
// Produces: Privacy_Report_{date}.pdf

import jsPDF from 'jspdf';
import { ScanResult, ScanFile, DETECTION_CONFIG, RISK_CONFIG } from '@/types';

function formatDate(date: Date): string {
  return date.toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function hexToRgb(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return [r, g, b];
}

export async function exportPDFReport(result: ScanResult, file: ScanFile): Promise<void> {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageW = 210;
  const pageH = 297;
  const margin = 20;
  const contentW = pageW - margin * 2;

  let y = 0;

  // ── HEADER ──────────────────────────────────────────────
  // Green header band
  doc.setFillColor(23, 76, 60);
  doc.rect(0, 0, pageW, 52, 'F');

  // Logo text
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(20);
  doc.text('Privacy Guardian', margin, 22);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  doc.setTextColor(200, 240, 220);
  doc.text('Privacy Risk Analysis Report', margin, 31);

  // Report date
  doc.setFontSize(9);
  doc.setTextColor(180, 220, 200);
  doc.text(`Generated: ${formatDate(result.completedAt)}`, margin, 40);
  doc.text(`Scan ID: ${result.id.slice(0, 12)}...`, margin, 47);

  y = 64;

  // ── SCAN SUMMARY ─────────────────────────────────────────
  doc.setTextColor(30, 30, 30);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  doc.text('Scan Summary', margin, y);
  y += 8;

  // Summary table
  const rows = [
    ['Filename', file.name],
    ['File Size', `${(file.size / (1024 * 1024)).toFixed(2)} MB`],
    ['File Type', file.type.split('/')[1]?.toUpperCase() || file.type],
    ['Privacy Score', `${result.privacyScore} / 100`],
    ['Risk Level', RISK_CONFIG[result.riskLevel].label],
    ['Items Detected', `${result.detections.length}`],
    ['Processing Time', `${(result.processingTime / 1000).toFixed(1)} seconds`],
    ['Analysis Date', formatDate(result.completedAt)],
  ];

  doc.setFontSize(9);
  rows.forEach(([label, value], i) => {
    const rowY = y + i * 9;
    // Alternating rows
    if (i % 2 === 0) {
      doc.setFillColor(246, 244, 239);
      doc.rect(margin, rowY - 4, contentW, 9, 'F');
    }
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(95, 99, 104);
    doc.text(label, margin + 3, rowY + 1);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(30, 30, 30);
    doc.text(value, margin + 55, rowY + 1);
  });

  y += rows.length * 9 + 14;

  // ── PRIVACY SCORE VISUALIZATION ──────────────────────────
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  doc.setTextColor(30, 30, 30);
  doc.text('Privacy Score', margin, y);
  y += 8;

  // Score bar background
  doc.setFillColor(229, 226, 218);
  doc.roundedRect(margin, y, contentW, 10, 2, 2, 'F');

  // Score bar fill
  const scoreColor = result.privacyScore >= 80 ? [30, 132, 73] as [number,number,number]
    : result.privacyScore >= 50 ? [214, 137, 16] as [number,number,number]
    : result.privacyScore >= 25 ? [192, 57, 43] as [number,number,number]
    : [146, 43, 33] as [number,number,number];

  doc.setFillColor(...scoreColor);
  const barWidth = (result.privacyScore / 100) * contentW;
  doc.roundedRect(margin, y, barWidth, 10, 2, 2, 'F');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.setTextColor(255, 255, 255);
  if (barWidth > 20) {
    doc.text(`${result.privacyScore}%`, margin + 4, y + 6.5);
  }
  y += 18;

  // Risk level badge
  const riskConfig = RISK_CONFIG[result.riskLevel];
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(...scoreColor);
  doc.text(`Risk Level: ${riskConfig.label}`, margin, y);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  doc.setTextColor(95, 99, 104);
  doc.text(riskConfig.description, margin + 55, y);
  y += 14;

  // ── DETECTED ITEMS ────────────────────────────────────────
  if (result.detections.length > 0) {
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(13);
    doc.setTextColor(30, 30, 30);
    doc.text(`Detected Items (${result.detections.length})`, margin, y);
    y += 8;

    // Table headers
    doc.setFillColor(23, 76, 60);
    doc.rect(margin, y - 4, contentW, 9, 'F');
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8);
    doc.setTextColor(255, 255, 255);
    doc.text('Type', margin + 3, y + 1);
    doc.text('Masked Value', margin + 50, y + 1);
    doc.text('Confidence', margin + 130, y + 1);
    doc.text('Redacted', margin + 160, y + 1);
    y += 9;

    doc.setFont('helvetica', 'normal');
    doc.setTextColor(30, 30, 30);

    result.detections.forEach((det, i) => {
      const config = DETECTION_CONFIG[det.type];
      const rowY = y + i * 9;

      if (i % 2 === 0) {
        doc.setFillColor(246, 244, 239);
        doc.rect(margin, rowY - 4, contentW, 9, 'F');
      }

      doc.setFontSize(8);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(30, 30, 30);
      doc.text(config.label, margin + 3, rowY + 1);

      doc.setFont('helvetica', 'normal');
      doc.setTextColor(95, 99, 104);
      doc.text(det.text || '—', margin + 50, rowY + 1, { maxWidth: 75 });

      doc.setFont('helvetica', 'bold');
      doc.setTextColor(...scoreColor);
      doc.text(`${det.confidence}%`, margin + 130, rowY + 1);

      doc.setTextColor(det.redacted ? 30 : 192, det.redacted ? 132 : 57, det.redacted ? 73 : 43);
      doc.setFont('helvetica', 'normal');
      doc.text(det.redacted ? '✓ Yes' : '○ No', margin + 160, rowY + 1);
    });

    y += result.detections.length * 9 + 14;
  }

  // ── RECOMMENDATIONS ───────────────────────────────────────
  if (result.recommendations.length > 0) {
    // Page break if needed
    if (y > 230) {
      doc.addPage();
      y = 20;
    }

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(13);
    doc.setTextColor(30, 30, 30);
    doc.text('Recommendations', margin, y);
    y += 10;

    result.recommendations.forEach((rec, i) => {
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(9);
      doc.setTextColor(30, 30, 30);
      doc.text(`${i + 1}.  ${rec}`, margin + 3, y, { maxWidth: contentW - 6 });
      y += 9;
    });

    y += 8;
  }

  // ── DISCLAIMER ────────────────────────────────────────────
  if (y > 250) {
    doc.addPage();
    y = 20;
  }

  doc.setFillColor(246, 244, 239);
  doc.roundedRect(margin, y, contentW, 28, 2, 2, 'F');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.setTextColor(95, 99, 104);
  doc.text('Important Disclaimer', margin + 4, y + 7);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(154, 160, 166);
  const disclaimer = 'AI detection may not identify all sensitive data. Confidence scores reflect model certainty, not guaranteed accuracy. Always manually review images before sharing, especially government IDs and financial documents.';
  doc.text(disclaimer, margin + 4, y + 14, { maxWidth: contentW - 8 });

  // ── FOOTER ───────────────────────────────────────────────
  const footerY = pageH - 14;
  doc.setFillColor(23, 76, 60);
  doc.rect(0, footerY - 4, pageW, 18, 'F');

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(180, 220, 200);
  doc.text('Privacy Guardian  ·  Confidential  ·  Generated by AI — Review before sharing', margin, footerY + 4);
  doc.text(`Page 1`, pageW - margin, footerY + 4, { align: 'right' });

  // Save
  const date = new Date().toISOString().split('T')[0];
  const safeFilename = file.name.replace(/[^a-z0-9]/gi, '_').toLowerCase();
  doc.save(`Privacy_Report_${safeFilename}_${date}.pdf`);
}
