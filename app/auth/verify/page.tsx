'use client'

import { Mail } from 'lucide-react'
import Link from 'next/link'

export default function VerifyEmailPage() {
  return (
    <div className="w-full flex flex-col items-center justify-center text-center space-y-6 animate-fade-in py-12">
      <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mb-4">
        <Mail className="w-10 h-10 text-primary animate-pulse-subtle" />
      </div>
      
      <h2 className="text-3xl font-bold tracking-tight text-primary-text">Check your email</h2>
      <p className="text-secondary-text max-w-sm">
        We&apos;ve sent a secure verification link to your email. Please click the link to verify your account.
      </p>

      <div className="pt-6 w-full space-y-3">
        <button 
          className="w-full flex justify-center py-3.5 px-4 border border-transparent rounded-xl shadow-md text-sm font-semibold text-white bg-primary hover:bg-primary-light transition-colors"
          onClick={() => window.open('https://mail.google.com', '_blank')}
        >
          Open Gmail
        </button>
        <div className="flex items-center gap-3 w-full">
          <button className="flex-1 py-3 px-4 border border-border rounded-xl text-sm font-semibold text-primary-text hover:bg-surface-elevated transition-colors">
            Resend Email
          </button>
          <Link href="/auth/signup" className="flex-1 py-3 px-4 border border-border rounded-xl text-sm font-semibold text-primary-text hover:bg-surface-elevated transition-colors">
            Change Email
          </Link>
        </div>
      </div>
    </div>
  )
}

