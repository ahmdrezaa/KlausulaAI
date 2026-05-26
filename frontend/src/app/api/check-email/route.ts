// frontend/src/app/api/check-email/route.ts
import { createClient } from '@/lib/supabase/server'
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  try {
    const { email } = await request.json()
    
    if (!email) {
      return NextResponse.json({ error: 'Email is required' }, { status: 400 })
    }
    
    // Gunakan supabase client biasa (bukan admin)
    const supabase = createClient()
    
    // Coba cek apakah email sudah terdaftar dengan sign in dummy
    // Ini akan return error "Invalid login credentials" jika email ada
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password: 'dummy_password_that_will_never_match_12345!',
    })
    
    // Jika error "Invalid login credentials" → email terdaftar
    // Jika error "Email not confirmed" → email terdaftar tapi belum verifikasi
    // Jika tidak ada error (tidak mungkin karena password dummy) atau error lain → email tidak terdaftar
    if (error?.message?.includes('Invalid login credentials') || 
        error?.message?.includes('Email not confirmed')) {
      return NextResponse.json({ exists: true })
    }
    
    // Email tidak terdaftar
    return NextResponse.json({ exists: false })
    
  } catch (error) {
    console.error('API error:', error)
    return NextResponse.json({ exists: false, error: 'Internal server error' }, { status: 500 })
  }
}