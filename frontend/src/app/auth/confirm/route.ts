// frontend/src/app/auth/confirm/route.ts
import { type EmailOtpType } from '@supabase/supabase-js'
import { type NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const token_hash = searchParams.get('token_hash')
  const type = searchParams.get('type') as EmailOtpType | null
  const next = searchParams.get('next') ?? '/dashboard'

  // Redirect to login if missing params
  if (!token_hash || !type) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  const supabase = createClient()

  const { error } = await supabase.auth.verifyOtp({
    type,
    token_hash,
  })

  if (error) {
    console.error('Auth confirmation error:', error)
    return NextResponse.redirect(new URL('/login?error=auth-failed', request.url))
  }

  // Redirect to dashboard on success
  return NextResponse.redirect(new URL(next, request.url))
}