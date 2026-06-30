import { Metadata } from 'next';
import { Navbar } from '@/components/ui/Navbar';
import { Check, Zap, Shield, Star } from 'lucide-react';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Pricing — Privacy Guardian',
  description: 'Simple, transparent pricing for individuals and teams.',
};

export default function PricingPage() {
  return (
    <main className="min-h-screen pb-20 overflow-hidden">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 sm:pt-24 relative z-10">
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 mb-4 px-4 py-1.5 rounded-full text-xs font-600 border border-primary/20 bg-primary/10 text-primary">
            <Zap size={11} className="fill-primary" />
            Industry-leading privacy protection
          </div>
          <h1 className="text-4xl sm:text-5xl font-800 tracking-tight mb-4 text-primary-text">
            Simple, <span className="text-primary">transparent</span> pricing.
          </h1>
          <p className="text-lg max-w-2xl mx-auto text-secondary-text">
            Start protecting your privacy for free. Upgrade when you need more volume or advanced features.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto items-center">

          {/* Basic (Free) */}
          <div className="glass-panel p-8 rounded-3xl flex flex-col transition-all duration-300 hover:-translate-y-1 relative overflow-hidden">
            <div className="mb-8">
              <h3 className="text-xl font-800 mb-2 text-primary-text">Basic</h3>
              <p className="text-sm text-secondary-text min-h-[40px]">Perfect for occasional personal use.</p>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="text-5xl font-900 text-primary-text">$0</span>
                <span className="text-lg font-500 text-secondary-text">/mo</span>
              </div>
            </div>

            <ul className="space-y-4 mb-8 flex-1">
              {[
                '5 scans per day',
                'Max file size: 5MB',
                'Standard face & text detection',
                '1 Trusted Face enrollment',
              ].map(item => (
                <li key={item} className="flex items-start gap-3">
                  <Check size={18} className="text-primary flex-shrink-0 mt-0.5" />
                  <span className="text-primary-text font-500">{item}</span>
                </li>
              ))}
            </ul>

            <Link
              href="/"
              className="block w-full py-3 px-4 text-center rounded-xl font-600 transition-all duration-200 hover:bg-surface-elevated bg-surface text-primary border border-border shadow-sm"
            >
              Get Started Free
            </Link>
          </div>

          {/* Pro — Most Popular */}
          <div className="p-8 rounded-3xl flex flex-col relative md:-translate-y-4 transition-all duration-300 hover:-translate-y-6 bg-primary/90 backdrop-blur-[40px] border border-primary/20 shadow-[0_16px_48px_rgba(23,76,60,0.25)]">
            {/* Most Popular badge */}
            <div
              className="absolute -top-4 left-1/2 -translate-x-1/2 px-5 py-1.5 rounded-full text-xs font-800 uppercase tracking-wider backdrop-blur-md border border-white/30"
              style={{ background: 'rgba(200, 169, 107, 0.7)', color: '#fff', boxShadow: '0 4px 16px rgba(200,169,107,0.4)' }}
            >
              Most Popular
            </div>

            <div className="mb-8">
              <h3 className="text-xl font-800 mb-2 text-white">Pro</h3>
              <p className="text-sm text-white/90 min-h-[40px]">
                For professionals who handle sensitive data daily.
              </p>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="text-5xl font-900 text-white">$1</span>
                <span className="text-lg font-500 text-white/90">/mo</span>
              </div>
            </div>

            <ul className="space-y-4 mb-8 flex-1">
              {[
                'Unlimited scans',
                'Max file size: 50MB',
                'Advanced detection (IDs, Cards, etc.)',
                'Unlimited Trusted Faces',
                'High-resolution PDF export',
              ].map(item => (
                <li key={item} className="flex items-start gap-3">
                  <Check size={18} className="text-brand-accent flex-shrink-0 mt-0.5" />
                  <span className="text-white font-500">{item}</span>
                </li>
              ))}
            </ul>

            <button
              className="block w-full py-3.5 px-4 text-center rounded-xl font-700 transition-all duration-200 hover:scale-[1.02] bg-surface text-primary shadow-sm"
            >
              Start 7-day free trial
            </button>
          </div>

          {/* Max */}
          <div className="glass-panel p-8 rounded-3xl flex flex-col transition-all duration-300 hover:-translate-y-1 relative overflow-hidden">
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-2">
                <h3 className="text-xl font-800 text-primary-text">Max</h3>
                <Star size={16} className="text-brand-accent fill-brand-accent" />
              </div>
              <p className="text-sm text-secondary-text min-h-[40px]">Custom solutions and API access for teams.</p>
              <div className="mt-4 flex items-baseline gap-1">
                <span className="text-5xl font-900 text-primary-text">$3</span>
                <span className="text-lg font-500 text-secondary-text">/mo</span>
              </div>
            </div>

            <ul className="space-y-4 mb-8 flex-1">
              {[
                'Everything in Pro',
                'REST API Access',
                'On-premise deployment options',
                'SSO / SAML authentication',
                'Dedicated success manager',
              ].map(item => (
                <li key={item} className="flex items-start gap-3">
                  <Check size={18} className="text-primary flex-shrink-0 mt-0.5" />
                  <span className="text-primary-text font-500">{item}</span>
                </li>
              ))}
            </ul>

            <Link href="/support" className="block w-full py-3 px-4 text-center rounded-xl font-600 transition-all duration-200 hover:bg-surface-elevated bg-surface text-primary border border-border shadow-sm">
              Contact Sales
            </Link>
          </div>
        </div>

        {/* Trust badges */}
        <div className="flex flex-wrap justify-center gap-6 mt-16">
          {[
            { icon: Shield, text: 'AES-256 Encryption' },
            { icon: Zap, text: '95.23% Detection Accuracy' },
            { icon: Star, text: 'No data stored ever' },
          ].map(({ icon: Icon, text }) => (
            <div
              key={text}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-500 glass-panel shadow-sm text-primary-text"
            >
              <Icon size={15} className="text-primary" />
              {text}
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
