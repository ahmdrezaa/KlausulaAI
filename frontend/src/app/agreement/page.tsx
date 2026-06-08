// src/app/agreement/page.tsx
// Halaman Persetujuan — Mockup 02
// Letakkan di: frontend/src/app/agreement/page.tsx

'use client'
import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { useAuth } from '@/contexts/AuthContext'
import toast from 'react-hot-toast'

export default function AgreementPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const email = searchParams.get('email') || ''
  const { user, supabase } = useAuth()
  
  const [agreed, setAgreed] = useState(false)
  const [subscribed, setSubscribed] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Redirect jika tidak ada user atau email
  useEffect(() => {
    if (!user && !email) {
      router.push('/login')
    }
  }, [user, email, router])

  const handleSubmit = async () => {
    if (!agreed) return
    
    setIsSubmitting(true)
    
    try {
      const currentUser = user
      
      if (!currentUser) {
        toast.error('User tidak ditemukan. Silakan login kembali.')
        router.push('/login')
        return
      }

      // Simpan agreement ke profiles
      const { error: profileError } = await supabase
        .from('profiles')
        .upsert({
          id: currentUser.id,
          email: currentUser.email,
          agreed_terms: true,
          subscribed_newsletter: subscribed,
          updated_at: new Date().toISOString(),
        }, {
          onConflict: 'id',
        })

      if (profileError) {
        console.error('Profile error:', profileError)
        toast.error('Gagal menyimpan persetujuan. Silakan coba lagi.')
        return
      }

      toast.success('Terima kasih! Mengarahkan ke onboarding...')
      router.push('/onboarding')
    } catch (error) {
      console.error('Submit error:', error)
      toast.error('Terjadi kesalahan. Silakan coba lagi.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="h-full flex flex-col"
      style={{ background: 'var(--bg-base)' }}>

      {/* Navbar */}
      <nav className="flex items-center justify-center px-4 py-4 md:px-10">
        <div className="flex items-center gap-2">
          <Image
            src="/icons/Logo_KlausulaAI.svg"
            alt="KlausulaAI Logo"
            width={28}
            height={28}
            style={{ color: "var(--accent)" }}
          />
          <span
            className="font-display text-2xl font-regular"
            style={{ color: "var(--text-secondary)" }}
          >
            KlausulaAI
          </span>
        </div>
      </nav>

      {/* Card */}
      <div className="w-full h-full flex flex-col items-center justify-center page-enter mb-16">
        <div className="w-full max-w-xl stagger">
          <h1 className="font-display text-5xl md:text-6xl font-regular text-center"
            style={{ color: 'var(--text-primary)' }}>
            Buat akun Anda
          </h1>
          <p className="text-center font-regular text-xl mb-10" style={{ color: 'var(--text-primary)' }}>
            Beberapa hal untuk ditinjau sebelum memulai
          </p>

          <div
            className="rounded-2xl border overflow-hidden"
            style={{ background: 'var(--bg-card)', borderColor: 'var(--border)', borderWidth: '0.5px' }}
          >
            {/* Checkbox 1 */}
            <label className="flex items-start gap-4 p-6 cursor-pointer hover:bg-white/5 transition-colors"
              onClick={() => setAgreed(!agreed)}>
              <div
                className="mt-0.5 w-5 h-5 rounded flex-shrink-0 border flex items-center justify-center transition-all"
                style={{
                  background: agreed ? 'var(--accent)' : 'transparent',
                  borderColor: agreed ? 'var(--accent)' : 'var(--border-light)',
                }}
              >
                {agreed && (
                  <svg width="12" height="10" viewBox="0 0 12 10" fill="none">
                    <path d="M1 5l3.5 3.5L11 1" stroke="var(--bg-base)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
              </div>
              <p className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                Saya menyetujui{' '}
                <a href="#" className="underline" style={{ color: 'var(--accent)' }} onClick={e => e.stopPropagation()}>
                  Syarat Layanan
                </a>
                {' '}dan{' '}
                <a href="#" className="underline" style={{ color: 'var(--accent)' }} onClick={e => e.stopPropagation()}>
                  Kebijakan Penggunaan
                </a>
                {' '}KlausulaAI, serta mengonfirmasi bahwa saya berusia minimal 17 tahun.
              </p>
            </label>

            <div className="h-px mx-6" style={{ background: 'var(--border)' }} />

            {/* Checkbox 2 */}
            <label className="flex items-start gap-4 p-6 cursor-pointer hover:bg-white/5 transition-colors"
              onClick={() => setSubscribed(!subscribed)}>
              <div
                className="mt-0.5 w-5 h-5 rounded flex-shrink-0 border flex items-center justify-center transition-all"
                style={{
                  background: subscribed ? 'var(--accent)' : 'transparent',
                  borderColor: subscribed ? 'var(--accent)' : 'var(--border-light)',
                }}
              >
                {subscribed && (
                  <svg width="12" height="10" viewBox="0 0 12 10" fill="none">
                    <path d="M1 5l3.5 3.5L11 1" stroke="var(--bg-base)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                )}
              </div>
              <p className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                Berlangganan notifikasi dan pembaruan fitur melalui email.
                Anda dapat berhenti berlangganan kapan saja.
              </p>
            </label>

            {/* Button */}
            <div className="px-6 pb-6">
              <button
                onClick={handleSubmit}
                disabled={!agreed}
                className="w-full py-3.5 rounded-xl font-semibold text-sm transition-all active:scale-[0.98]"
                style={{
                  background: agreed ? 'var(--text-primary)' : 'var(--bg-elevated)',
                  color: agreed ? 'var(--bg-base)' : 'var(--text-disabled)',
                  cursor: agreed ? 'pointer' : 'not-allowed',
                }}
              >
                Buat Akun
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function ScaleIcon() {
  return (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v1M3 9h18M7 9l-3 6a3 3 0 006 0L7 9zM17 9l-3 6a3 3 0 006 0L17 9zM12 4l8 5M12 4L4 9M12 21v-6M9 21h6"/>
    </svg>
  )
}
