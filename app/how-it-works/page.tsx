import { Metadata } from 'next';
import { Navbar } from '@/components/ui/Navbar';
import { Upload, ShieldCheck, Zap } from 'lucide-react';
import Link from 'next/link';
import { InteractiveDemo } from '@/components/ui/InteractiveDemo';

export const metadata: Metadata = {
  title: 'How it Works — Privacy Guardian',
  description: 'Understand how Privacy Guardian detects and redacts your sensitive information in three simple steps.',
};

export default function HowItWorksPage() {
  return (
    <main className="min-h-screen pb-20">
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 sm:pt-24">
        <div className="text-center mb-16">
          <h1 className="text-4xl sm:text-5xl font-800 text-primary-text tracking-tight mb-4">
            Privacy in <span className="text-primary">Three Steps</span>
          </h1>
          <p className="text-lg text-secondary-text max-w-2xl mx-auto">
            Our AI runs directly in your browser to keep your data safe. Here is exactly what happens when you use Privacy Guardian.
          </p>
        </div>

        <InteractiveDemo />

        <div className="space-y-12 relative mt-16">
          <div className="hidden md:block absolute left-8 top-10 bottom-10 w-0.5 bg-brand-border" />

          {/* Step 1 */}
          <div className="relative flex flex-col md:flex-row gap-6 md:gap-12 items-start">
            <div className="flex-shrink-0 w-16 h-16 rounded-2xl bg-surface border border-border flex items-center justify-center shadow-sm relative z-10">
              <Upload className="text-primary" size={28} />
            </div>
            <div className="flex-1 glass-panel p-8 rounded-2xl shadow-sm">
              <div className="text-sm font-700 text-primary tracking-wider uppercase mb-2">Step 1</div>
              <h2 className="text-2xl font-800 text-primary-text mb-3">Upload Securely</h2>
              <p className="text-secondary-text leading-relaxed">
                Drop your image or PDF into the browser. Unlike traditional cloud services, your file is immediately processed 
                using local machine learning models. We use AES-256 encryption in transit for any supplementary API calls, 
                but the heavy lifting stays on your device.
              </p>
            </div>
          </div>

          {/* Step 2 */}
          <div className="relative flex flex-col md:flex-row gap-6 md:gap-12 items-start">
            <div className="flex-shrink-0 w-16 h-16 rounded-2xl bg-primary border border-primary-dark flex items-center justify-center shadow-soft relative z-10">
              <Zap className="text-white" size={28} />
            </div>
            <div className="flex-1 glass-panel p-8 rounded-2xl shadow-sm">
              <div className="text-sm font-700 text-primary tracking-wider uppercase mb-2">Step 2</div>
              <h2 className="text-2xl font-800 text-primary-text mb-3">AI Detection</h2>
              <p className="text-secondary-text leading-relaxed">
                Our specialized Privacy Engine scans your document for sensitive entities:
              </p>
              <ul className="mt-4 space-y-2 text-secondary-text">
                <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary" /> Faces (except Trusted Faces you enroll)</li>
                <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary" /> Government IDs (Aadhaar, PAN, SSN)</li>
                <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary" /> Phone numbers and Emails</li>
                <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-primary" /> Credit cards and Bank account numbers</li>
              </ul>
            </div>
          </div>

          {/* Step 3 */}
          <div className="relative flex flex-col md:flex-row gap-6 md:gap-12 items-start">
            <div className="flex-shrink-0 w-16 h-16 rounded-2xl bg-surface border border-border flex items-center justify-center shadow-sm relative z-10">
              <ShieldCheck className="text-primary" size={28} />
            </div>
            <div className="flex-1 glass-panel p-8 rounded-2xl shadow-sm">
              <div className="text-sm font-700 text-primary tracking-wider uppercase mb-2">Step 3</div>
              <h2 className="text-2xl font-800 text-primary-text mb-3">Redact & Export</h2>
              <p className="text-secondary-text leading-relaxed">
                Detected items are permanently obscured using non-reversible pixelation and solid color blocking.
                You can review the AI&apos;s confidence scores, adjust the bounding boxes if needed, and export the safe 
                version as a high-quality PDF or Image.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-16 text-center">
          <Link 
            href="/"
            className="inline-flex items-center gap-2 px-6 py-3 text-sm font-600 text-white bg-primary hover:bg-primary-dark rounded-xl transition-all shadow-soft"
          >
            Try it for free
          </Link>
        </div>
      </div>
    </main>
  );
}

