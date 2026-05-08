// src/app/welcome/page.tsx
// Halaman Welcome "Selamat Datang di KlausulaAI" — Mockup 04
// Letakkan di: frontend/src/app/welcome/page.tsx

"use client";
import { useRouter } from "next/navigation";
import Image from "next/image";

export default function WelcomePage() {
  const router = useRouter();

  // TODO: Navigasi ke halaman konfigurasi projek baru
  const handleNewProject = () => router.push("/new-project");

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-6 py-10 page-enter"
      style={{ background: "var(--bg-base)" }}
    >
      {/* Big scale icon */}
      <div className="mb-2 slide-up">
        <Image
          src="/icons/Logo_KlausulaAI.svg"
          alt="KlausulaAI Logo"
          width={200}
          height={200}
          style={{ color: "var(--accent)" }}
        />
      </div>

      <div className="text-center stagger">
        <h1
          className="font-display text-6xl font-regular mb-2"
          style={{ color: "var(--accent)" }}
        >
          Selamat Datang di KlausulaAI
        </h1>
        <p
          className="text-xl leading-relaxed mb-12"
          style={{ color: "var(--text-primary)" }}
        >
          Mulai analisis hukum Anda dengan membuat projek
          <br />
          pertama. Semua percakapan, dokumen, dan referensi
          <br />
          tersimpan rapi dalam satu projek.
        </p>

        <button
          onClick={handleNewProject}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border font-medium text-sm transition-all hover:opacity-80 active:scale-[0.97]"
          style={{
            background: "transparent",
            borderColor: "var(--text-primary)",
            color: "var(--text-primary)",
          }}
        >
          + Buat Projek Baru
        </button>
      </div>
    </div>
  );
}

function BigScaleIcon() {
  return (
    <svg
      width="120"
      height="120"
      viewBox="0 0 100 100"
      fill="none"
      stroke="var(--text-primary)"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {/* Base */}
      <rect
        x="38"
        y="85"
        width="24"
        height="4"
        rx="2"
        fill="var(--text-primary)"
        stroke="none"
      />
      {/* Pole */}
      <line x1="50" y1="20" x2="50" y2="86" />
      {/* Top bar */}
      <line x1="20" y1="30" x2="80" y2="30" />
      {/* Left chain */}
      <line x1="20" y1="30" x2="14" y2="52" />
      <line x1="20" y1="30" x2="26" y2="52" />
      {/* Right chain */}
      <line x1="80" y1="30" x2="74" y2="52" />
      <line x1="80" y1="30" x2="86" y2="52" />
      {/* Left pan */}
      <path d="M10 52 Q20 62 30 52" strokeWidth="2.5" />
      {/* Right pan */}
      <path d="M70 52 Q80 62 90 52" strokeWidth="2.5" />
      {/* Top ornament */}
      <circle cx="50" cy="18" r="4" fill="var(--text-primary)" stroke="none" />
    </svg>
  );
}
