// app/not-found.tsx — Custom 404 page
import Link from 'next/link';
import { Shield, ArrowLeft } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/8 border border-primary/15 mb-6">
          <Shield size={28} className="text-primary" />
        </div>
        <h1 className="text-3xl font-800 text-primary-text mb-3">Page not found</h1>
        <p className="text-secondary-text mb-8">
          The scan or page you&apos;re looking for doesn&apos;t exist, or may have expired.
          Scans are automatically deleted after 24 hours.
        </p>
        <Link
          href="/"
          className="inline-flex items-center gap-2 bg-primary text-white font-600 text-sm px-6 py-3 rounded-xl hover:bg-primary-dark transition-colors shadow-cta"
        >
          <ArrowLeft size={15} />
          Back to Privacy Guardian
        </Link>
      </div>
    </div>
  );
}

