import Link from 'next/link'
import { Shield, Lock, Trash2, GlobeLock } from 'lucide-react'

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-background selection:bg-primary/10">
      {/* Left Column - Brand & Trust (40%) */}
      <div className="hidden lg:flex w-[40%] bg-primary-dark text-white flex-col relative overflow-hidden">
        {/* Abstract Background Elements */}
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden opacity-20 pointer-events-none">
          <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full bg-primary blur-3xl" />
          <div className="absolute bottom-0 right-0 w-[500px] h-[500px] rounded-full bg-primary-light blur-[100px]" />
        </div>

        <div className="relative z-10 flex flex-col h-full p-12 justify-between">
          <div>
            <Link href="/" className="inline-flex items-center gap-2 mb-16">
              <Shield className="w-8 h-8 text-brand-accent" />
              <span className="font-bold text-xl tracking-tight">Privacy Guardian</span>
            </Link>

            <h1 className="text-4xl lg:text-5xl font-bold leading-tight mb-6">
              Protect your privacy before you share.
            </h1>
            <p className="text-brand-subtle text-lg max-w-md">
              Trusted by professionals to detect sensitive information before it reaches the internet.
            </p>
          </div>

          <div className="space-y-6 bg-white/5 backdrop-blur-md p-8 rounded-2xl border border-white/10">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                <Lock className="w-5 h-5 text-brand-accent" />
              </div>
              <p className="font-medium text-white">End-to-end encrypted scans</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                <Trash2 className="w-5 h-5 text-brand-accent" />
              </div>
              <p className="font-medium text-white">Files automatically deleted</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                <Shield className="w-5 h-5 text-brand-accent" />
              </div>
              <p className="font-medium text-white">Zero data selling guarantee</p>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center shrink-0">
                <GlobeLock className="w-5 h-5 text-brand-accent" />
              </div>
              <p className="font-medium text-white">GDPR & CCPA Ready</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right Column - Auth Card (60%) */}
      <div className="flex-1 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-20 xl:px-32 relative">
        {/* Mobile Logo */}
        <Link href="/" className="lg:hidden absolute top-8 left-6 inline-flex items-center gap-2">
          <Shield className="w-6 h-6 text-primary" />
          <span className="font-bold text-lg text-primary tracking-tight">Privacy Guardian</span>
        </Link>
        
        <div className="w-full max-w-[420px] mx-auto">
          {children}
        </div>
      </div>
    </div>
  )
}

