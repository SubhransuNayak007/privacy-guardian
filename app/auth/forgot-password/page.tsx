'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Mail } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'

export default function ForgotPasswordPage() {
  const supabase = createClient()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/auth/reset-password`,
      })
      if (error) throw error
      setSuccess(true)
    } catch (err: any) {
      setError(err.message || 'Failed to send reset link.')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="w-full flex flex-col items-center justify-center text-center space-y-6 animate-fade-in py-12">
        <div className="w-16 h-16 bg-success/10 rounded-full flex items-center justify-center mb-4">
          <Mail className="w-8 h-8 text-success" />
        </div>
        <h2 className="text-3xl font-bold tracking-tight text-primary-text">Check your inbox</h2>
        <p className="text-secondary-text max-w-sm">
          We sent a secure password reset link to <span className="font-semibold text-primary-text">{email}</span>.
        </p>
        <div className="pt-6 w-full">
          <Link 
            href="/auth/signin" 
            className="w-full flex justify-center py-3.5 px-4 border border-border rounded-xl shadow-sm text-sm font-semibold text-primary-text bg-surface hover:bg-surface-elevated transition-colors"
          >
            Return to Login
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full flex flex-col space-y-8 animate-fade-in py-8">
      <div>
        <Link href="/auth/signin" className="inline-flex items-center text-sm font-medium text-secondary-text hover:text-primary transition-colors mb-6">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to login
        </Link>
        <h2 className="text-3xl font-bold tracking-tight text-primary-text mb-2">Reset Password</h2>
        <p className="text-secondary-text">Enter your email and we&apos;ll send you a secure reset link.</p>
      </div>

      {error && (
        <div className="p-4 bg-brand-danger/5 border border-brand-danger/20 rounded-lg text-brand-danger text-sm flex items-start gap-3">
          <div className="mt-0.5">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          </div>
          <div>
            <p className="font-semibold">Error</p>
            <p>{error}</p>
          </div>
        </div>
      )}

      <form onSubmit={handleReset} className="space-y-6">
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-primary-text" htmlFor="email">
            Email Address
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-3 bg-surface border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all shadow-sm text-primary-text placeholder:text-muted-text"
            placeholder="you@company.com"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !email}
          className="w-full flex justify-center py-3.5 px-4 border border-transparent rounded-xl shadow-md text-sm font-semibold text-white bg-primary hover:bg-primary-light focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary transition-colors disabled:opacity-70 disabled:cursor-not-allowed"
        >
          {loading ? (
            <div className="flex items-center gap-3">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-accent opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-accent"></span>
              </span>
              <span className="animate-pulse">Sending secure link...</span>
            </div>
          ) : (
            'Send Reset Link'
          )}
        </button>
      </form>
    </div>
  )
}

