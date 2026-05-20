'use client'
import { useState } from 'react'
import { supabase } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const router = useRouter()

  // Magic Link Login (Email OTP)
  const handleEmailLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`
      }
    })

    if (error) {
      setMessage(`Error: ${error.message}`)
    } else {
      setMessage('Cek email Anda untuk link masuk!')
    }
    setLoading(false)
  }

  // Google OAuth Login
  const handleGoogleLogin = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`
      }
    })
    if (error) setMessage(`Error: ${error.message}`)
  }

  return (
    <div className="min-h-screen bg-[#1a0f0a] flex items-center justify-center">
      <div className="flex gap-20 items-center max-w-6xl w-full px-8">
        
        {/* Left Side */}
        <div className="flex-1">
          <p className="text-[#c4783a] text-sm mb-2">Asisten Hukum Berbasis AI</p>
          <h1 className="text-white text-5xl font-bold leading-tight mb-4">
            Analisis hukum lebih{' '}
            <span className="text-[#c4783a]">cepat</span> & lebih{' '}
            <span className="text-[#c4783a]">akurat</span>
          </h1>
          <p className="text-gray-400 text-base">
            KlausulaAI adalah workspace hukum bertenaga AI untuk mahasiswa 
            dan praktisi hukum Indonesia. Analisis kontrak, riset pasal, 
            dan drafting dokumen dalam satu platform.
          </p>
        </div>

        {/* Right Side - Auth Form */}
        <div className="w-[380px] bg-[#2a1a12] border border-[#3d2a1e] rounded-xl p-8">
          
          {/* Google Login */}
          <button
            onClick={handleGoogleLogin}
            className="w-full flex items-center justify-center gap-3 bg-white text-gray-800 
                       py-3 rounded-lg font-medium hover:bg-gray-100 transition mb-4"
          >
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Lanjutkan dengan Google
          </button>

          <div className="flex items-center gap-3 my-4">
            <hr className="flex-1 border-[#3d2a1e]" />
            <span className="text-gray-500 text-sm">atau</span>
            <hr className="flex-1 border-[#3d2a1e]" />
          </div>

          {/* Email Form */}
          <form onSubmit={handleEmailLogin}>
            <input
              type="email"
              placeholder="Masukkan email Anda"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full bg-[#1a0f0a] border border-[#3d2a1e] text-white 
                         placeholder-gray-500 rounded-lg px-4 py-3 mb-3 
                         focus:outline-none focus:border-[#c4783a]"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#c4783a] text-white py-3 rounded-lg font-medium 
                         hover:bg-[#a85e2a] transition disabled:opacity-50"
            >
              {loading ? 'Mengirim...' : 'Lanjutkan dengan email'}
            </button>
          </form>

          {/* Message */}
          {message && (
            <p className={`mt-3 text-sm text-center ${
              message.includes('Error') ? 'text-red-400' : 'text-green-400'
            }`}>
              {message}
            </p>
          )}

          {/* Terms */}
          <p className="text-gray-500 text-xs text-center mt-4">
            Dengan melanjutkan, Anda menyetujui{' '}
            <a href="/terms" className="text-[#c4783a] underline">Syarat Layanan</a>
            {' '}dan{' '}
            <a href="/privacy" className="text-[#c4783a] underline">Kebijakan Privasi</a>
            {' '}kami.
          </p>

          {/* Switch to Register */}
          <p className="text-gray-500 text-sm text-center mt-4">
            Belum punya akun?{' '}
            <button
              onClick={() => router.push('/register')}
              className="text-[#c4783a] underline"
            >
              Daftar sekarang
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}