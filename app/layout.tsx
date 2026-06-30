import type { Metadata, Viewport } from 'next';
import { JetBrains_Mono, Instrument_Serif } from 'next/font/google';
import { GeistSans } from 'geist/font/sans';
import './globals.css';
import { ThemeProvider } from '@/components/theme-provider';
import { SpaceBackground } from '@/components/ui/SpaceBackground';

const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'], display: 'swap', variable: '--font-jetbrains' });
const instrumentSerif = Instrument_Serif({ weight: '400', subsets: ['latin'], display: 'swap', variable: '--font-instrument' });

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#174C3C',
};

export const metadata: Metadata = {
  title: {
    default: 'Privacy Guardian — Protect What You Share',
    template: '%s — Privacy Guardian',
  },
  description:
    'Enterprise-grade image privacy. Detect exposed personal data — phone numbers, Aadhaar, bank details, faces — and create a safe redacted version instantly.',
  keywords: [
    'image redaction', 'privacy', 'PII detection', 'face blur',
    'Aadhaar redaction', 'GDPR compliance', 'data privacy', 'photo privacy',
  ],
  authors: [{ name: 'Privacy Guardian' }],
  robots: { index: true, follow: true },
  openGraph: {
    title: 'Privacy Guardian — Protect What You Share',
    description: 'AI-powered image privacy. Detect and redact sensitive information before you share.',
    type: 'website',
    locale: 'en_IN',
    siteName: 'Privacy Guardian',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Privacy Guardian',
    description: 'Detect and redact sensitive info in images before sharing.',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${instrumentSerif.variable} ${jetbrainsMono.variable}`} suppressHydrationWarning>
      <body className={`font-sans bg-background min-h-screen antialiased`} suppressHydrationWarning>
        <ThemeProvider attribute="class" defaultTheme="light" disableTransitionOnChange>
          <SpaceBackground />
          <div id="app-root" className="relative z-0">
            {children}
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
