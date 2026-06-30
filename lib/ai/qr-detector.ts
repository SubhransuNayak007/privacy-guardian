import jsQR from 'jsqr';

export interface QRCodeMatch {
  text: string;
  bbox: { x: number; y: number; width: number; height: number }; // normalized 0-1
}

export async function detectQRCodes(imageFile: File | Blob): Promise<QRCodeMatch[]> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(imageFile);
    
    img.onload = () => {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          throw new Error('Could not get 2d context for QR detection');
        }
        
        ctx.drawImage(img, 0, 0);
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        
        // jsQR only finds the *most prominent* QR code by default, which is usually sufficient for ID cards
        const code = jsQR(imageData.data, imageData.width, imageData.height);
        
        const results: QRCodeMatch[] = [];
        if (code) {
          // Calculate bounding box and normalize
          const minX = Math.min(code.location.topLeftCorner.x, code.location.bottomLeftCorner.x);
          const minY = Math.min(code.location.topLeftCorner.y, code.location.topRightCorner.y);
          const maxX = Math.max(code.location.topRightCorner.x, code.location.bottomRightCorner.x);
          const maxY = Math.max(code.location.bottomLeftCorner.y, code.location.bottomRightCorner.y);
          
          results.push({
            text: code.data,
            bbox: {
              x: minX / img.width,
              y: minY / img.height,
              width: (maxX - minX) / img.width,
              height: (maxY - minY) / img.height,
            }
          });
        }
        
        URL.revokeObjectURL(url);
        resolve(results);
      } catch (err) {
        URL.revokeObjectURL(url);
        reject(err);
      }
    };
    
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to load image for QR detection'));
    };
    
    img.src = url;
  });
}
