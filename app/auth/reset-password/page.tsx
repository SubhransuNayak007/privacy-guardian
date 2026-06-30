'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { createClient } from '@/lib/supabase/client'
import { CheckCircle2 } from 'lucide-react'

export default function ResetPasswordPage() {
  const router = useRouter()
  const supabase = createClient()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

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

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    
    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      setLoading(false)
      return
    }
    
    try {
      const { error } = await supabase.auth.updateUser({
        password: password
      })
      if (error) throw error
      setSuccess(true)
      setTimeout(() => {
        router.push('/dashboard')
      }, 2000)
    } catch (err: any) {
      setError(err.message || 'Failed to update password.')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="w-full flex flex-col items-center justify-center text-center space-y-6 animate-fade-in py-12">
        <div className="w-16 h-16 bg-success/10 rounded-full flex items-center justify-center mb-4">
          <CheckCircle2 className="w-8 h-8 text-success" />
        </div>
        <h2 className="text-3xl font-bold tracking-tight text-primary-text">Password Updated</h2>
        <p className="text-secondary-text max-w-sm">
          Your password has been successfully reset. Redirecting to your workspace...
        </p>
      </div>
    )
  }

  return (
    <div className="w-full flex flex-col space-y-8 animate-fade-in py-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-primary-text mb-2">Create New Password</h2>
        <p className="text-secondary-text">Please enter your new strong password below.</p>
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

      <form onSubmit={handleUpdate} className="space-y-6">
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-primary-text" htmlFor="password">
            New Password
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
            Confirm New Password
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

        <button
          type="submit"
          disabled={loading || !password || !confirmPassword}
          className="w-full flex justify-center py-3.5 px-4 border border-transparent rounded-xl shadow-md text-sm font-semibold text-white bg-primary hover:bg-primary-light focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary transition-colors disabled:opacity-70 disabled:cursor-not-allowed"
        >
          {loading ? (
            <div className="flex items-center gap-3">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-accent opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-brand-accent"></span>
              </span>
              <span className="animate-pulse">Updating password...</span>
            </div>
          ) : (
            'Update Password'
          )}
        </button>
      </form>
    </div>
  )
}

