import { NextResponse, type NextRequest } from 'next/server'

/**
 * Next.js 16 proxy (replaces legacy middleware.ts).
 * Auth is disabled for local dev — all routes are open.
 * Only adds security headers.
 */
export function proxy(request: NextRequest) {
  const response = NextResponse.next()

  // Security Headers
  response.headers.set('X-Frame-Options', 'DENY')
  response.headers.set('X-Content-Type-Options', 'nosniff')
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')

  return response
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
