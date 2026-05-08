// src/app/new-project/page.tsx
// Halaman Konfigurasi Projek Baru — Mockup 05
// Letakkan di: frontend/src/app/new-project/page.tsx

"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Image from "next/image";

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [masterPrompt, setMasterPrompt] = useState("");

  // TODO: Simpan projek baru ke Supabase (tabel: chat_sessions / projects)
  //       lalu redirect ke /dashboard?projectId=<id>
  const handleCreate = () => {
    if (!name.trim()) return;
    // Sementara langsung ke dashboard
    router.push("/dashboard");
  };

  const handleCancel = () => router.back();

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

      {/* Form */}
      <main className="w-full flex-1 flex items-center justify-center px-6 py-10 mb-16">
        <div className="w-full max-w-2xl stagger">
          <h1
            className="font-display text-5xl md:text-6xl font-regular mb-10"
            style={{ color: "var(--text-primary)" }}
          >
            Konfigurasi Projek Baru
          </h1>

          <div className="space-y-6">
            {/* Nama Projek */}
            <div>
              <label
                className="block text-sm font-medium mb-2"
                style={{ color: "var(--accent)" }}
              >
                Nama Projek
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="cth. Sengketa Lahan Blok A"
                className="w-full px-4 py-3.5 rounded-xl text-sm outline-none transition-all border focus:border-[var(--accent)]"
                style={{
                  background: "var(--bg-input)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                }}
              />
            </div>

            {/* Deskripsi Singkat */}
            <div>
              <label
                className="block text-sm font-medium mb-2"
                style={{ color: "var(--accent)" }}
              >
                Deskripsi Singkat
              </label>
              <input
                type="text"
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                placeholder="Ringkasan konteks projek ini ..."
                className="w-full px-4 py-3.5 rounded-xl text-sm outline-none transition-all border focus:border-[var(--accent)]"
                style={{
                  background: "var(--bg-input)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                }}
              />
            </div>

            {/* Master Prompt */}
            <div>
              <label
                className="block text-sm font-medium mb-2"
                style={{ color: "var(--accent)" }}
              >
                Master Prompt
              </label>
              <textarea
                rows={4}
                value={masterPrompt}
                onChange={(e) => setMasterPrompt(e.target.value)}
                placeholder="Berperanlah sebagai pengacara senior spesialis hukum perdata. Gunakan bahasa formal dan referensi pasal yang akurat. Setiap jawaban harus disertai dasar hukum yang relevan"
                className="w-full px-4 py-3.5 rounded-xl text-sm outline-none transition-all border focus:border-[var(--accent)] resize-none"
                style={{
                  background: "var(--bg-input)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                  lineHeight: "1.6",
                }}
              />
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={handleCancel}
                className="px-6 py-3 rounded-xl font-medium text-sm border transition-all hover:opacity-80 active:scale-[0.97]"
                style={{
                  background: "transparent",
                  borderColor: "var(--border-light)",
                  color: "var(--text-secondary)",
                }}
              >
                Batal
              </button>
              <button
                onClick={handleCreate}
                disabled={!name.trim()}
                className="px-6 py-3 rounded-xl font-semibold text-sm transition-all active:scale-[0.97]"
                style={{
                  background: name.trim()
                    ? "var(--text-primary)"
                    : "var(--bg-elevated)",
                  color: name.trim()
                    ? "var(--bg-base)"
                    : "var(--text-disabled)",
                  cursor: name.trim() ? "pointer" : "not-allowed",
                }}
              >
                Buat Projek
              </button>
            </div>
          </div>
        </div>
      </main>
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
