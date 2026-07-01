'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Lock, Clock, ChevronRight, UserPlus, Menu, X } from 'lucide-react';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { TrustedFacesModal } from '@/components/ui/TrustedFacesModal';
import { Logo } from '@/components/ui/Logo';

export function Navbar() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  
  return (
    <motion.nav
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="sticky top-0 z-50 bg-surface-glass backdrop-blur-[32px] border-b border-border saturate-150"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <div className="relative w-8 h-8 rounded-lg flex items-center justify-center overflow-hidden text-primary">
              <Logo className="w-8 h-8" />
            </div>
            <div>
              <span className="font-700 text-primary-text text-[15px] tracking-tight">Privacy</span>
              <span className="font-700 text-primary text-[15px] tracking-tight"> Guardian</span>
            </div>
          </Link>

          {/* Center nav - Desktop */}
          <div className="hidden md:flex absolute left-1/2 -translate-x-1/2 items-center gap-6">
            <NavLink href="/">Home</NavLink>
            <NavLink href="/how-it-works">How it works</NavLink>
            <NavLink href="/security">Security</NavLink>
            <NavLink href="/pricing">Pricing</NavLink>
            <NavLink href="/support">Support</NavLink>
          </div>

          {/* Right actions - Desktop */}
          <div className="hidden md:flex items-center gap-3">
            <ThemeToggle />
            
            {/* Trust badge */}
            <div className="flex items-center gap-1.5 text-xs text-secondary-text border border-border rounded-full px-3 py-1.5">
              <Lock size={11} className="text-primary" />
              <span>AES-256 Encrypted</span>
            </div>
            
            {/* Trusted Faces Button */}
            <button
              onClick={() => setIsModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-2 text-sm font-600 text-primary bg-primary/10 hover:bg-primary/20 rounded-lg transition-colors"
            >
              <UserPlus size={15} />
              <span>Trusted Faces</span>
            </button>
          </div>
          
          {/* Mobile actions & menu button */}
          <div className="md:hidden flex items-center gap-2">
            <ThemeToggle />
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 -mr-2 text-secondary-text hover:text-primary-text"
            >
              {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </div>
      
      {/* Mobile Menu */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="md:hidden border-t border-border bg-surface overflow-hidden"
          >
            <div className="px-4 py-4 space-y-4">
              <div className="flex flex-col gap-2">
                <Link href="/" onClick={() => setIsMobileMenuOpen(false)} className={`text-sm font-500 py-2 border-b border-border ${usePathname() === '/' ? 'text-primary' : 'text-primary-text'}`}>Home</Link>
                <Link href="/how-it-works" onClick={() => setIsMobileMenuOpen(false)} className={`text-sm font-500 py-2 border-b border-border ${usePathname() === '/how-it-works' ? 'text-primary' : 'text-primary-text'}`}>How it works</Link>
                <Link href="/security" onClick={() => setIsMobileMenuOpen(false)} className={`text-sm font-500 py-2 border-b border-border ${usePathname() === '/security' ? 'text-primary' : 'text-primary-text'}`}>Security</Link>
                <Link href="/pricing" onClick={() => setIsMobileMenuOpen(false)} className={`text-sm font-500 py-2 border-b border-border ${usePathname() === '/pricing' ? 'text-primary' : 'text-primary-text'}`}>Pricing</Link>
                <Link href="/support" onClick={() => setIsMobileMenuOpen(false)} className={`text-sm font-500 py-2 ${usePathname() === '/support' ? 'text-primary' : 'text-primary-text'}`}>Support</Link>
              </div>
              
              {/* Mobile CTA */}
              <div className="p-4 flex flex-col gap-3">
                <Link 
                  href="/auth/signin"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className="flex items-center justify-center w-full py-2.5 text-sm font-600 text-primary-text bg-surface-elevated rounded-xl border border-border"
                >
                  Sign In
                </Link>
                <button
                  onClick={() => { setIsMobileMenuOpen(false); setIsModalOpen(true); }}
                  className="flex items-center justify-center gap-1.5 w-full py-2.5 text-sm font-600 text-primary bg-primary/10 rounded-xl"
                >
                  <UserPlus size={15} />
                  Trusted Faces
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Trusted Faces Modal */}
      {isModalOpen && <TrustedFacesModal onClose={() => setIsModalOpen(false)} />}
    </motion.nav>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const isActive = pathname === href;

  return (
    <Link
      href={href}
      className={`relative text-sm font-500 transition-colors duration-150 py-1 ${
        isActive
          ? 'text-primary'
          : 'text-secondary-text hover:text-primary-text'
      }`}
    >
      {children}
      {isActive && (
        <motion.div
          layoutId="navbar-active"
          className="absolute -bottom-1.5 left-0 right-0 h-0.5 bg-primary rounded-full"
          transition={{ type: "spring", stiffness: 400, damping: 30 }}
        />
      )}
    </Link>
  );
}

export function PrivacyNotice() {
  return (
    <div className="flex items-center gap-2 text-xs text-secondary-text">
      <div className="flex items-center gap-1.5 bg-surface border border-border rounded-full px-3 py-1.5">
        <Lock size={11} className="text-primary" />
        <span>Files encrypted in transit</span>
      </div>
      <div className="flex items-center gap-1.5 bg-surface border border-border rounded-full px-3 py-1.5">
        <Clock size={11} className="text-secondary-text" />
        <span>Deleted after processing</span>
      </div>
      <div className="hidden sm:flex items-center gap-1.5 bg-surface border border-border rounded-full px-3 py-1.5">
        <Shield size={11} className="text-primary" />
        <span>GDPR compliant</span>
      </div>
    </div>
  );
}

