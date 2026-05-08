// src/app/onboarding/page.tsx
// Halaman Onboarding "Sebelum obrolan pertama" — Mockup 03
// Letakkan di: frontend/src/app/onboarding/page.tsx

"use client";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";

const FEATURES = [
  {
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M12 8v4M12 16h.01" />
      </svg>
    ),
    title: "Bukan pengganti advokat",
    desc: "KlausulaAI adalah alat bantu riset dan analisis. Selalu konsultasikan keputusan hukum penting kepada advokat berlisensi.",
  },
  {
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
    ),
    title: "Percakapan tersimpan per projek",
    desc: "Semua obrolan, dokumen, dan referensi dikelompokkan dalam projek sehingga mudah dilanjutkan kapan saja.",
  },
  {
    icon: (
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </svg>
    ),
    title: "Sepenuhnya gratis",
    desc: "Akses penuh ke semua fitur KlausulaAI tanpa biaya berlangganan termasuk projek tak terbatas, upload dokumen, dan referensi pasal otomatis.",
  },
];

export default function OnboardingPage() {
  const router = useRouter();

  // TODO: Tandai onboarding selesai di Supabase user metadata
  const handleStart = () => router.push("/welcome");

  return (
    <div
      className="h-full flex flex-col"
      style={{ background: "var(--bg-base)" }}
    >
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

      <div className="w-full h-full flex flex-col items-center justify-center page-enter mb-16">

        <div className="w-full max-w-2xl stagger">
          <h1
            className="font-display text-5xl md:text-6xl font-regular text-center mb-2"
            style={{ color: "var(--text-primary)" }}
          >
            Sebelum obrolan pertama
          </h1>
          <p
            className="text-center text-xl mb-10"
            style={{ color: "var(--text-primary)" }}
          >
            Beberapa hal yang perlu Anda ketahui
          </p>

          <div
            className="rounded-2xl border overflow-hidden"
            style={{ background: "var(--bg-card)", borderColor: "var(--border)" }}
          >
            <div className="p-6 space-y-6">
              {FEATURES.map((f, i) => (
                <div key={i} className="flex gap-4 items-start">
                  <div
                    className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-lg"
                    style={{
                      color: "var(--accent)",
                      background: "var(--bg-elevated)",
                    }}
                  >
                    {f.icon}
                  </div>
                  <div>
                    <p
                      className="font-semibold text-sm mb-1"
                      style={{ color: "var(--text-primary)" }}
                    >
                      {f.title}
                    </p>
                    <p
                      className="text-sm leading-relaxed"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {f.desc}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <div className="px-6 pb-6">
              <button
                onClick={handleStart}
                className="w-full py-3.5 rounded-xl font-semibold text-sm transition-all hover:opacity-90 active:scale-[0.98]"
                style={{
                  background: "var(--text-primary)",
                  color: "var(--bg-base)",
                }}
              >
                Mulai menggunakan KlausulaAI
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ScaleIcon() {
  return (
    <svg
      width="26"
      height="26"
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
