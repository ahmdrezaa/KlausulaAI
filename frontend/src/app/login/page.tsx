// src/app/login/page.tsx
// Halaman Login — Mockup 01
// Letakkan di: frontend/src/app/login/page.tsx

"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";
import { useState } from "react";
import toast from "react-hot-toast";

export default function LoginPage() {
  const router = useRouter();
  const { checkEmailExists, signInWithGoogle } = useAuth();
  const [email, setEmail] = useState("");
  const [isChecking, setIsChecking] = useState(false);

  const handleCheckEmail = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email) {
      toast.error("Silakan masukkan email Anda.");
      return;
    }

    setIsChecking(true);

    try {
      const exists = await checkEmailExists(email);

      if (exists) {
        // Email terdaftar → arahkan ke login password
        toast.success("Email terdaftar! Silakan masukkan password.");
        router.push(`/login-password?email=${encodeURIComponent(email)}`);
      } else {
        // Email belum terdaftar → arahkan ke register
        toast.success("Email belum terdaftar. Silakan buat akun.");
        router.push(`/register?email=${encodeURIComponent(email)}`);
      }
    } catch (error) {
      console.error(error);
      toast.error("Terjadi kesalahan. Silakan coba lagi.");
    } finally {
      setIsChecking(false);
    }
  };

  const handleGoogle = async () => {
    try {
      await signInWithGoogle();
    } catch (error) {
      console.error(error);
      toast.error("Gagal login dengan Google");
    }
  };

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--bg-base)" }}
    >
      {/* Navbar */}
      <nav className="flex items-center justify-between px-4 py-4 md:px-10">
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
        <Link
          href="/login"
          className="text-sm"
          style={{ color: "var(--text-primary)" }}
        >
          Tentang kami
        </Link>
      </nav>

      {/* Main content */}
      <main className="w-full flex-1 flex items-center justify-center px-6 py-10 mb-16">
        <div className="w-full max-w-7xl flex flex-col md:flex-row gap-12 md:gap-20 items-center page-enter">
          {/* Left — hero text */}
          <div className="w-6/12 flex-1 text-center md:text-left stagger">
            <p
              className="font-display text-4xl font-regular"
              style={{ color: "var(--accent)" }}
            >
              Asisten Hukum Berbasis AI
            </p>
            <h1
              className="font-display text-6xl md:text-6xl lg:text-7xl font-regular leading-tight mb-1"
              style={{ color: "var(--text-primary)" }}
            >
              Analisis hukum lebih{" "}
              <span style={{ color: "var(--accent)" }}>cepat</span> & lebih{" "}
              <span style={{ color: "var(--accent)" }}>akurat</span>
            </h1>
            <p
              className="text-2xl pt-1 leading-tight mx-auto md:mx-0"
              style={{ color: "var(--text-primary)" }}
            >
              KlausulaAI adalah workspace hukum bertenaga AI
              <br />
              untuk mahasiswa dan praktisi hukum Indonesia.
              <br />
              Analisis kontrak, riset pasal, dan drafting
              <br />
              dokumen dalam satu platform.
            </p>
          </div>

          {/* Right — login card */}
          <div
            className="w-full md:w-[420px] rounded-2xl p-8 border"
            style={{
              background: "var(--bg-base)",
              borderColor: "var(--border)",
            }}
          >
            {/* Google login */}
            <button
              onClick={handleGoogle}
              className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl border font-medium text-sm transition-all hover:opacity-90 active:scale-[0.98] mb-5"
              style={{
                background: "var(--bg-base)",
                borderColor: "var(--border-light)",
                color: "var(--text-primary)",
              }}
            >
              <Image
                src="/icons/Google_Icon.svg"
                alt="KlausulaAI Logo"
                width={18}
                height={18}
                style={{ color: "var(--accent)" }}
              />
              Lanjutkan dengan Google
            </button>

            <div className="flex items-center gap-3 mb-5">
              <div
                className="flex-1 h-px"
                style={{ background: "var(--border)" }}
              />
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                atau
              </span>
              <div
                className="flex-1 h-px"
                style={{ background: "var(--border)" }}
              />
            </div>

            {/* Email form */}
            {/* TODO: Hubungkan dengan Supabase Auth */}
            <form onSubmit={handleCheckEmail} className="space-y-3">
              <input
                type="email"
                placeholder="Masukkan email Anda"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-xl text-sm outline-none transition-all border focus:border-[var(--accent)]"
                style={{
                  background: "var(--bg-input)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                }}
              />
              <button
                type="submit"
                className="w-full py-3 px-4 rounded-xl font-medium text-sm transition-all hover:opacity-90 active:scale-[0.98]"
                style={{
                  background: "var(--text-primary)",
                  color: "var(--bg-base)",
                }}
              >
                Lanjutkan dengan email
              </button>
            </form>

            <p
              className="text-xs text-center mt-5 leading-relaxed"
              style={{ color: "var(--text-muted)" }}
            >
              Dengan melanjutkan, Anda menyetujui{" "}
              <a
                href="#"
                className="underline"
                style={{ color: "var(--text-secondary)" }}
              >
                Syarat Layanan
              </a>{" "}
              dan{" "}
              <a
                href="#"
                className="underline"
                style={{ color: "var(--text-secondary)" }}
              >
                Kebijakan Privasi
              </a>{" "}
              kami.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}

function ScaleIcon() {
  return (
    <svg
      width="28"
      height="28"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--accent)"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 3v1M3 9h18M7 9l-3 6a3 3 0 006 0L7 9zM17 9l-3 6a3 3 0 006 0L17 9zM12 4l8 5M12 4L4 9M12 21v-6M9 21h6" />
    </svg>
  );
}
