// app/scanning/[scanId]/page.tsx
import { Metadata } from 'next';
import { Navbar } from '@/components/ui/Navbar';
import { ScanningScreen } from '@/components/screens/ScanningScreen';

export const metadata: Metadata = {
  title: 'Scanning — Privacy Guardian',
  description: 'Analyzing your image for privacy risks.',
};

interface Props {
  params: Promise<{ scanId: string }>;
}

export default async function ScanningPage({ params }: Props) {
  const { scanId } = await params;
  return (
    <main>
      <Navbar />
      <ScanningScreen scanId={scanId} />
    </main>
  );
}
