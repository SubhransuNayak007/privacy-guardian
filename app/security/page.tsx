import { Metadata } from 'next';
import { Navbar } from '@/components/ui/Navbar';
import { Shield, Lock, Trash2, Cpu } from 'lucide-react';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Security & Trust — Privacy Guardian',
  description: 'Bank-grade security. Zero Trust Architecture. See how we keep your data safe.',
};

export default function SecurityPage() {
  return (
    <main className="min-h-screen pb-20">
      <Navbar />
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 sm:pt-24">
        <div className="text-center mb-16">
          <h1 className="text-4xl sm:text-5xl font-800 text-primary-text tracking-tight mb-4">
            Bank-grade Security.<br />
            <span className="text-primary">Zero Trust Architecture.</span>
          </h1>
          <p className="text-lg text-secondary-text max-w-2xl mx-auto">
            Privacy isn&apos;t just our name, it&apos;s our foundational architecture. 
            We built Privacy Guardian so that even we can&apos;t access your sensitive data.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 mb-16">
          {/* Card 1 */}
          <div className="glass-panel p-8 rounded-2xl shadow-sm hover:shadow-soft transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-6">
              <Cpu className="text-primary" size={24} />
            </div>
            <h3 className="text-xl font-800 text-primary-text mb-3">Local Processing First</h3>
            <p className="text-secondary-text leading-relaxed">
              We utilize WebAssembly and local machine learning models that run entirely in your browser. 
              For many tasks, your files literally never leave your computer&apos;s RAM.
            </p>
          </div>

          {/* Card 2 */}
          <div className="glass-panel p-8 rounded-2xl shadow-sm hover:shadow-soft transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-6">
              <Lock className="text-primary" size={24} />
            </div>
            <h3 className="text-xl font-800 text-primary-text mb-3">AES-256 Encryption</h3>
            <p className="text-secondary-text leading-relaxed">
              Any data that must be transmitted for advanced cloud processing is encrypted in transit using TLS 1.3 
              and encrypted at rest using military-grade AES-256 standards.
            </p>
          </div>

          {/* Card 3 */}
          <div className="glass-panel p-8 rounded-2xl shadow-sm hover:shadow-soft transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-6">
              <Trash2 className="text-primary" size={24} />
            </div>
            <h3 className="text-xl font-800 text-primary-text mb-3">Zero Retention Policy</h3>
            <p className="text-secondary-text leading-relaxed">
              We delete your files from our servers the exact millisecond the processing pipeline completes. 
              There are no archives, no backups, and no hidden databases of your uploads.
            </p>
          </div>

          {/* Card 4 */}
          <div className="glass-panel p-8 rounded-2xl shadow-sm hover:shadow-soft transition-shadow">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-6">
              <Shield className="text-primary" size={24} />
            </div>
            <h3 className="text-xl font-800 text-primary-text mb-3">No AI Training</h3>
            <p className="text-secondary-text leading-relaxed">
              Your sensitive data is yours. We explicitly prohibit the use of any user-uploaded content 
              for training our machine learning models. Period.
            </p>
          </div>
        </div>

        <div className="bg-primary rounded-3xl p-8 sm:p-12 text-center text-white shadow-soft">
          <h2 className="text-3xl font-800 mb-4">Enterprise Compliance ready.</h2>
          <p className="text-brand-subtle text-lg mb-8 max-w-xl mx-auto">
            GDPR, CCPA, and SOC2 readiness built-in. Want to deploy Privacy Guardian on-premise for your organization?
          </p>
          <Link href="/support" className="inline-block px-6 py-3 font-600 text-primary-text bg-surface hover:bg-surface-elevated rounded-xl transition-colors">
            Contact Security Team
          </Link>
        </div>
      </div>
    </main>
  );
}

