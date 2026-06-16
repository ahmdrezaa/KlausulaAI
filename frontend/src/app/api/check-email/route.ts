// frontend/src/app/api/check-email/route.ts
import { createAdminClient } from '@/lib/supabase/admin'
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  try {
    const { email } = await request.json()

    if (!email) {
      return NextResponse.json(
        { error: 'Email is required' },
        { status: 400 }
      )
    }

    // Validasi format email sederhana
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(email)) {
      return NextResponse.json(
        { error: 'Invalid email format' },
        { status: 400 }
      )
    }

    // Gunakan admin client untuk list users
    const supabase = createAdminClient()

    const {
      data: { users },
      error,
    } = await supabase.auth.admin.listUsers()

    if (error) {
      console.error('Admin API error:', error)
      return NextResponse.json(
        { exists: false, error: error.message },
        { status: 500 }
      )
    }

    // Cek apakah email sudah terdaftar
    const exists = users.some((user: any) => user.email === email)

    console.log(`🔍 Email check: ${email} -> ${exists ? 'TERDAFTAR' : 'BELUM TERDAFTAR'}`)

    return NextResponse.json({ exists })
  } catch (error) {
    console.error('API error:', error)
    return NextResponse.json(
      { exists: false, error: 'Internal server error' },
      { status: 500 }
    )
  }
}