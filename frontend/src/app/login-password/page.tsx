// frontend/src/app/login-password/page.tsx
'use client'
import { useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { useAuth } from '@/contexts/AuthContext'
import toast from 'react-hot-toast'

export default function LoginPasswordPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const email = searchParams.get('email') || ''
  const { signIn } = useAuth()
  
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!password) {
      toast.error('Silakan masukkan password Anda.')
      return
    }

    setIsSubmitting(true)
    try {
      const { error } = await signIn(email, password)
      
      if (error) {
        toast.error('Email atau password salah.')
        return
      }
      
      toast.success('Login berhasil!')
      router.push('/dashboard')
    } catch (error) {
      toast.error('Gagal login. Silakan coba lagi.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--bg-base)" }}>
      <nav className="flex items-center justify-between px-4 py-4 md:px-10">
        <div className="flex items-center gap-2">
          <Image src="/icons/Logo_KlausulaAI.svg" alt="Logo" width={28} height={28} />
          <span className="font-display text-2xl">KlausulaAI</span>
        </div>
        <Link href="/login" className="text-sm">Kembali</Link>
      </nav>

      <main className="flex-1 flex items-center justify-center px-6 py-10">
        <div className="w-full max-w-md">
          <div className="rounded-2xl p-8 border">
            <h1 className="text-2xl font-bold text-center mb-2">Masukkan Password</h1>
            <p className="text-center text-sm mb-6" style={{ color: "var(--text-muted)" }}>
              Untuk akun {email}
            </p>

            <form onSubmit={handleSubmit} className="space-y-3">
              <input
                type="password"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-xl text-sm border"
                autoFocus
              />
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-3 px-4 rounded-xl font-medium text-sm"
                style={{ background: "var(--text-primary)", color: "var(--bg-base)" }}
              >
                {isSubmitting ? "Memproses..." : "Login"}
              </button>
            </form>

            <p className="text-center text-xs mt-5">
              <Link href="/login" className="underline" style={{ color: "var(--accent)" }}>
                Gunakan email lain
              </Link>
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}