// app/page.tsx — Upload screen (root route)
import { Metadata } from 'next';
import { Navbar } from '@/components/ui/Navbar';
import { UploadScreen } from '@/components/screens/UploadScreen';

export const metadata: Metadata = {
  title: 'Privacy Guardian — Protect What You Share',
  description: 'AI-powered image privacy. Detect exposed personal data — phone numbers, Aadhaar, faces, bank details — and create a safe redacted version instantly.',
};

export default function HomePage() {
  return (
    <main>
      <a href="#main-content" className="skip-link">Skip to main content</a>
      <Navbar />
      <div id="main-content">
        <UploadScreen />
      </div>
    </main>
  );
}
