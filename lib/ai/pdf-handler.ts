/**
 * Converts the first page of a PDF file to an Image Blob.
 */
export async function convertPdfToImage(file: File | Blob): Promise<Blob> {
  // Dynamically import pdfjs-dist to prevent "DOMMatrix is not defined" SSR evaluation error
  const pdfjsLib = await import('pdfjs-dist');
  
  if (!pdfjsLib.GlobalWorkerOptions.workerSrc) {
    pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';
  }

  const arrayBuffer = await file.arrayBuffer();
  
  // Load PDF document
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
  
  // Get first page
  const page = await pdf.getPage(1);
  
  // Set scale to get a high-quality render (e.g. 2.0 or 3.0)
  const viewport = page.getViewport({ scale: 2.0 });
  
  // Prepare canvas
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');
  
  if (!context) {
    throw new Error('Failed to get 2D context for PDF render');
  }
  
  canvas.height = viewport.height;
  canvas.width = viewport.width;
  
  // Render PDF page into canvas context
  await page.render({
    canvasContext: context,
    viewport: viewport
  } as any).promise;
  
  // Convert canvas to blob
  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error('Failed to convert PDF canvas to Blob'));
    }, 'image/jpeg', 0.95);
  });
}
