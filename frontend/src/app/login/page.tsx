// src/app/login/page.tsx
// Halaman Login — Mockup 01
// Letakkan di: frontend/src/app/login/page.tsx

"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Image from "next/image";

export default function LoginPage() {
  const router = useRouter();

  // TODO: Ganti dengan Supabase Auth (Google OAuth)
  const handleGoogle = () => router.push("/register");

  // TODO: Ganti dengan Supabase Auth (email)
  const handleEmail = (e: React.FormEvent) => {
    e.preventDefault();
    router.push("/register");
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
              className="text-2xl leading-tight mx-auto md:mx-0"
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
              <GoogleIcon />
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
            <form onSubmit={handleEmail} className="space-y-3">
              <input
                type="email"
                placeholder="Masukkan email Anda"
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

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24">
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  );
}
