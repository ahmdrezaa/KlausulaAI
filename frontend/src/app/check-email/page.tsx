// src/app/check-email/page.tsx
// Halaman Check Email — Mockup 01
// Letakkan di: frontend/src/app/check-email/page.tsx

"use client";
import Link from "next/link";
import { EnvelopeIcon } from "@heroicons/react/24/outline";

export default function CheckEmailPage() {
  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{ background: "var(--bg-base)" }}
    >
      <div className="text-center max-w-xl px-6">
        <div className="flex justify-center mb-6">
          <div
            className="p-4 rounded-full"
            style={{ background: "rgba(var(--accent-rgb), 0.1)" }}
          >
            <EnvelopeIcon
              className="w-32 h-32"
              style={{ color: "var(--accent)" }}
            />
          </div>
        </div>
        <h1
          className="font-display text-5xl md:text-6xl font-regular text-center mb-2"
          style={{ color: "var(--text-primary)" }}
        >
          Cek email Anda
        </h1>
        <p
          className="text-center text-xl mb-10"
          style={{ color: "var(--text-primary)" }}
        >
          Kami telah mengirimkan link login ke email Anda. Klik link tersebut
          untuk masuk ke akun Anda.
        </p>
        <Link
          href="/login"
          className="inline-block px-6 py-3 rounded-lg font-medium transition-all"
          style={{ background: "var(--accent)", color: "white" }}
        >
          Kembali ke Login
        </Link>
      </div>
    </div>
  );
}
