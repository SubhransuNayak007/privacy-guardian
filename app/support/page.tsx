import { Navbar } from '@/components/ui/Navbar';
import { Mail, HelpCircle } from 'lucide-react';

const LinkedinIcon = ({ size = 24, className = "" }) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    width={size} 
    height={size} 
    viewBox="0 0 24 24" 
    fill="none" 
    stroke="currentColor" 
    strokeWidth="2" 
    strokeLinecap="round" 
    strokeLinejoin="round" 
    className={className}
  >
    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path>
    <rect x="2" y="9" width="4" height="12"></rect>
    <circle cx="4" cy="4" r="2"></circle>
  </svg>
);

export default function SupportPage() {
  return (
    <main className="min-h-screen text-primary-text flex flex-col">
      <Navbar />
      <div className="flex-1 max-w-4xl w-full mx-auto px-4 py-16">
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-900 mb-4 text-primary">Support & Contact</h1>
          <p className="text-lg text-secondary-text">We're here to help. Reach out to us or browse our FAQs.</p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 mb-16">
          <a
            href="mailto:cosmiccrumbs.07@gmail.com"
            className="flex flex-col items-center justify-center p-8 glass-panel rounded-3xl shadow-sm hover:shadow-md transition-shadow group"
          >
            <div className="w-16 h-16 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <Mail size={32} />
            </div>
            <h3 className="text-xl font-800 mb-2">Email Us</h3>
            <span className="text-primary font-600 hover:underline transition-colors text-center break-all">
              cosmiccrumbs.07@gmail.com
            </span>
          </a>

          <a
            href="https://www.linkedin.com/in/subhransu-nayak-4b33383a7?utm_source=share_via&utm_content=profile&utm_medium=member_android"
            target="_blank"
            rel="noopener noreferrer"
            className="flex flex-col items-center justify-center p-8 glass-panel rounded-3xl shadow-sm hover:shadow-md transition-shadow group"
          >
            <div className="w-16 h-16 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <LinkedinIcon size={32} />
            </div>
            <h3 className="text-xl font-800 mb-2">Connect on LinkedIn</h3>
            <span className="text-primary font-600 hover:underline transition-colors text-center">
              Privacy Guardian
            </span>
          </a>
        </div>

        <div className="glass-panel p-8 md:p-12 rounded-3xl shadow-sm">
          <div className="flex items-center gap-3 mb-8">
            <HelpCircle size={28} className="text-primary" />
            <h2 className="text-2xl font-800">Frequently Asked Questions</h2>
          </div>
          
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-700 mb-2">Is my data secure?</h3>
              <p className="text-secondary-text leading-relaxed">Yes. All processing is done locally in your browser. We never upload, store, or share your documents with any external servers.</p>
            </div>
            <div>
              <h3 className="text-lg font-700 mb-2">How do Trusted Faces work?</h3>
              <p className="text-secondary-text leading-relaxed">When you enroll a trusted face, we generate a secure mathematical representation of it. During scans, any faces in your document that match this representation are automatically skipped by the redaction engine.</p>
            </div>
            <div>
              <h3 className="text-lg font-700 mb-2">What file formats are supported?</h3>
              <p className="text-secondary-text leading-relaxed">We currently support standard image formats (JPEG, PNG, WEBP) and PDF documents.</p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

