import { get, set, del } from 'idb-keyval';
import { ScanResult, ScanFile } from '@/types';

export interface SavedSession {
  result: ScanResult;
  fileDataUrl: string;
  fileMetadata: Omit<ScanFile, 'originalFile'>;
}

export async function saveScanSession(scanId: string, result: ScanResult, file: ScanFile, fileBase64: string) {
  try {
    const session: SavedSession = {
      result,
      fileDataUrl: fileBase64,
      fileMetadata: {
        id: file.id,
        name: file.name,
        size: file.size,
        dimensions: file.dimensions,
        type: file.type,
        previewUrl: '', // omit the transient blob url
        uploadedAt: file.uploadedAt
      }
    };
    await set(`scan_${scanId}`, session);
  } catch (error) {
    console.error('Failed to save scan session to IndexedDB:', error);
  }
}

export async function getScanSession(scanId: string): Promise<SavedSession | undefined> {
  try {
    return await get(`scan_${scanId}`);
  } catch (error) {
    console.error('Failed to get scan session from IndexedDB:', error);
    return undefined;
  }
}

export async function deleteScanSession(scanId: string) {
  try {
    await del(`scan_${scanId}`);
  } catch (error) {
    console.error('Failed to delete scan session from IndexedDB:', error);
  }
}

/** Utility to convert a File or Blob into a Base64 string */
export function fileToBase64(file: File | Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = (error) => reject(error);
  });
}
