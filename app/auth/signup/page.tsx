'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Phone, CheckCircle2 } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'

export default function SignUpPage() {
  const router = useRouter()
  const supabase = createClient()
  
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [acceptedTerms, setAcceptedTerms] = useState(false)
  
  const [error, setError] = React.useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // Evaluate password strength
  const passwordStrength = React.useMemo(() => {
    let score = 0
    if (password.length > 0) {
      if (password.length > 7) score += 1
      if (/[A-Z]/.test(password)) score += 1
      if (/[0-9]/.test(password)) score += 1
      if (/[^A-Za-z0-9]/.test(password)) score += 1
    }

    let label = 'Weak'
    let color = 'bg-brand-danger'
    if (score === 2) { label = 'Fair'; color = 'bg-brand-warning' }
    if (score === 3) { label = 'Strong'; color = 'bg-primary-light' }
    if (score >= 4) { label = 'Excellent'; color = 'bg-success' }
    if (password.length === 0) { score = 0; label = ''; color = 'bg-surface-elevated' }

    return { score, label, color }
  }, [password])

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      setLoading(false)
      return
    }
    
    if (!acceptedTerms) {
      setError('You must accept the privacy policy to continue.')
      setLoading(false)
      return
    }
    
    try {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: name,
          },
          emailRedirectTo: `${window.location.origin}/auth/callback`,
        }
      })
      if (error) throw error
      router.push('/auth/verify')
    } catch (err: any) {
      setError(err.message || 'Failed to create account.')
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleSignUp = async () => {
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
        }
      })
      if (error) throw error
    } catch (err: any) {
      setError('Failed to initialize Google signup.')
    }
  }

  return (
    <div className="w-full flex flex-col space-y-6 animate-fade-in py-8">
      <div className="text-center sm:text-left">
        <h2 className="text-3xl font-bold tracking-tight text-primary-text mb-2">Create Account</h2>
        <p className="text-secondary-text">Join the standard in privacy protection.</p>
      </div>

      {error && (
        <div className="p-4 bg-brand-danger/5 border border-brand-danger/20 rounded-lg text-brand-danger text-sm flex items-start gap-3">
          <div className="mt-0.5">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          </div>
          <div>
            <p className="font-semibold">Registration Error</p>
            <p>{error}</p>
          </div>
        </div>
      )}



      <form onSubmit={handleSignUp} className="space-y-4">
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-primary-text" htmlFor="name">
            Full Name
          </label>
          <input
            id="name"
            type="text"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-4 py-3 bg-surface border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all shadow-sm text-primary-text placeholder:text-muted-text"
            placeholder="Jane Doe"
          />
        </div>

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

        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-primary-text" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-3 bg-surface border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all shadow-sm text-primary-text"
            placeholder="••••••••"
          />
          
          {/* Password Strength Indicator */}
          {password.length > 0 && (
            <div className="pt-1 animate-fade-in">
              <div className="flex gap-1 mb-1">
                {[1, 2, 3, 4].map((level) => (
                  <div 
                    key={level} 
                    className={`h-1.5 w-full rounded-full transition-colors duration-300 ${passwordStrength.score >= level ? passwordStrength.color : 'bg-surface-elevated'}`}
                  />
                ))}
              </div>
              <p className={`text-xs font-medium text-right ${passwordStrength.score >= 3 ? 'text-success' : 'text-secondary-text'}`}>
                {passwordStrength.label}
              </p>
            </div>
          )}
        </div>

        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-primary-text" htmlFor="confirmPassword">
            Confirm Password
          </label>
          <input
            id="confirmPassword"
            type="password"
            autoComplete="new-password"
            required
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-4 py-3 bg-surface border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-all shadow-sm text-primary-text"
            placeholder="••••••••"
          />
        </div>

        <div className="flex items-start pt-2">
          <div className="flex items-center h-5">
            <input
              id="terms"
              type="checkbox"
              required
              checked={acceptedTerms}
              onChange={(e) => setAcceptedTerms(e.target.checked)}
              className="h-4 w-4 rounded border-border text-primary focus:ring-primary"
            />
          </div>
          <div className="ml-3 text-sm">
            <label htmlFor="terms" className="text-secondary-text">
              I accept the <a href="#" className="text-primary hover:underline">Privacy Policy</a> and <a href="#" className="text-primary hover:underline">Terms of Service</a>.
            </label>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full flex justify-center mt-2 py-3.5 px-4 border border-transparent rounded-xl shadow-md text-sm font-semibold text-white bg-primary hover:bg-primary-light focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary transition-colors disabled:opacity-70 disabled:cursor-not-allowed"
        >
          {loading ? (
            <div className="flex items-center gap-3">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-accent opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-accent"></span>
              </span>
              <span className="animate-pulse">Verifying account...</span>
            </div>
          ) : (
            'Create Account'
          )}
        </button>
      </form>

      <div className="pt-2">
        <Link 
          href="/auth/otp" 
          className="w-full flex justify-center py-3 px-4 border border-border rounded-xl shadow-sm text-sm font-semibold text-primary-text bg-background hover:bg-surface-elevated focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary transition-colors"
        >
          <Phone className="w-5 h-5 mr-2 text-secondary-text" />
          Sign up with Phone
        </Link>
      </div>

      <p className="text-center text-sm text-secondary-text">
        Already have an account?{' '}
        <Link href="/auth/signin" className="font-semibold text-primary hover:text-primary-light transition-colors">
          Sign In
        </Link>
      </p>
    </div>
  )
}

