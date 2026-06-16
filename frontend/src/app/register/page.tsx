// frontend/src/app/register/page.tsx
"use client";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";
import toast from "react-hot-toast";

export default function RegisterPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const emailFromUrl = searchParams.get("email") || "";

  const { signUp } = useAuth();

  const [email, setEmail] = useState(emailFromUrl);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email || !password) {
      toast.error("Silakan isi email dan password.");
      return;
    }

    if (password.length < 6) {
      toast.error("Password minimal 6 karakter.");
      return;
    }

    if (password !== confirmPassword) {
      toast.error("Password dan konfirmasi password tidak sama.");
      return;
    }

    setIsSubmitting(true);

    try {
      const { error } = await signUp(email, password);

      if (error) {
        if (error.message?.toLowerCase().includes("already registered")) {
          toast.error("Email sudah terdaftar. Silakan login.");
          router.push("/login");
        } else {
          toast.error(error.message || "Registrasi gagal. Silakan coba lagi.");
        }
        return;
      }

      // Registrasi berhasil! Langsung arahkan ke halaman agreement
      toast.success("Pendaftaran berhasil!");
      router.push(`/agreement?email=${encodeURIComponent(email)}`);
    } catch (error) {
      console.error(error);
      toast.error("Terjadi kesalahan. Silakan coba lagi.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Jika tidak ada email dari URL, redirect ke login
  if (!emailFromUrl) {
    router.push("/login");
    return null;
  }

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
        <div className="w-full max-w-md stagger">
          <h1
            className="font-display text-5xl md:text-6xl font-regular mb-10"
            style={{ color: "var(--text-primary)" }}
          >
            Daftar Akun Baru
          </h1>

          <div className="space-y-6">
            {/* Tombol Google */}
            {/* <button
              onClick={handleGoogle}
              className="w-full flex items-center justify-center gap-3 py-3.5 px-4 rounded-xl text-sm font-medium transition-all hover:opacity-80 active:scale-[0.97] border"
              style={{
                background: "transparent",
                borderColor: "var(--border)",
                color: "var(--text-primary)",
              }}
            >
              <Image
                src="/icons/Google_Icon.svg"
                alt="Google"
                width={18}
                height={18}
              />
              Daftar dengan Google
            </button> */}

            {/* Separator */}
            <div className="flex items-center gap-3">
              <div
                className="flex-1 h-px"
                style={{ background: "var(--border)" }}
              />
              <span
                className="text-xs"
                style={{ color: "var(--text-muted)" }}
              >
                atau
              </span>
              <div
                className="flex-1 h-px"
                style={{ background: "var(--border)" }}
              />
            </div>

            {/* Form Fields */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label
                  className="block text-sm font-medium mb-2"
                  style={{ color: "var(--accent)" }}
                >
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="email@contoh.com"
                  className="w-full px-4 py-3.5 rounded-xl text-sm outline-none transition-all border focus:border-[var(--accent)]"
                  style={{
                    background: "var(--bg-input)",
                    borderColor: "var(--border)",
                    color: "var(--text-primary)",
                  }}
                  required
                />
              </div>

              <div>
                <label
                  className="block text-sm font-medium mb-2"
                  style={{ color: "var(--accent)" }}
                >
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Minimal 6 karakter"
                  className="w-full px-4 py-3.5 rounded-xl text-sm outline-none transition-all border focus:border-[var(--accent)]"
                  style={{
                    background: "var(--bg-input)",
                    borderColor: "var(--border)",
                    color: "var(--text-primary)",
                  }}
                />
              </div>

              <div>
                <label
                  className="block text-sm font-medium mb-2"
                  style={{ color: "var(--accent)" }}
                >
                  Konfirmasi Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Ulangi password"
                  className="w-full px-4 py-3.5 rounded-xl text-sm outline-none transition-all border focus:border-[var(--accent)]"
                  style={{
                    background: "var(--bg-input)",
                    borderColor: "var(--border)",
                    color: "var(--text-primary)",
                  }}
                />
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => router.back()}
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
                  type="submit"
                  disabled={isSubmitting}
                  className="px-6 py-3 rounded-xl font-semibold text-sm transition-all active:scale-[0.97]"
                  style={{
                    background: !isSubmitting && email && password && confirmPassword
                      ? "var(--text-primary)"
                      : "var(--bg-elevated)",
                    color: !isSubmitting && email && password && confirmPassword
                      ? "var(--bg-base)"
                      : "var(--text-disabled)",
                    cursor: !isSubmitting && email && password && confirmPassword
                      ? "pointer"
                      : "not-allowed",
                  }}
                >
                  {isSubmitting ? "Memproses..." : "Daftar"}
                </button>
              </div>
            </form>

            {/* Link ke Login */}
            <div className="text-center pt-4">
              <span
                className="text-sm"
                style={{ color: "var(--text-muted)" }}
              >
                Sudah punya akun?{" "}
              </span>
              <button
                onClick={() => router.push("/login")}
                className="text-sm font-medium transition-all hover:opacity-70"
                style={{ color: "var(--accent)" }}
              >
                Masuk di sini
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
