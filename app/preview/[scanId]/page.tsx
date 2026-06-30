// app/preview/[scanId]/page.tsx
import { Metadata } from 'next';
import { Navbar } from '@/components/ui/Navbar';
import { PreviewScreen } from '@/components/screens/PreviewScreen';

export const metadata: Metadata = {
  title: 'Preview — Privacy Guardian',
  description: 'Review your uploaded image before privacy analysis.',
};

interface Props {
  params: Promise<{ scanId: string }>;
}

export default async function PreviewPage({ params }: Props) {
  const { scanId } = await params;
  return (
    <main>
      <Navbar />
      <PreviewScreen scanId={scanId} />
    </main>
  );
}
