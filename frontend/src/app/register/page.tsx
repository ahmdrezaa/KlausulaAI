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

  const { signUp, signInWithGoogle } = useAuth();

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
        if (error.message.includes("already registered")) {
          toast.error("Email sudah terdaftar. Silakan login.");
          router.push("/login");
        } else {
          toast.error(error.message);
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

  const handleGoogle = async () => {
    try {
      await signInWithGoogle();
    } catch (error) {
      console.error(error);
      toast.error("Gagal daftar dengan Google");
    }
  };

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--bg-base)" }}
    >
      <nav className="flex items-center justify-between px-4 py-4 md:px-10">
        <div className="flex items-center gap-2">
          <Image
            src="/icons/Logo_KlausulaAI.svg"
            alt="Logo"
            width={28}
            height={28}
          />
          <span className="font-display text-2xl">KlausulaAI</span>
        </div>
        <Link href="/login" className="text-sm">
          Sudah punya akun? Login
        </Link>
      </nav>

      <main className="flex-1 flex items-center justify-center px-6 py-10">
        <div className="w-full max-w-md">
          <div className="rounded-2xl p-8 border">
            <h1 className="text-2xl font-bold text-center mb-6">
              Daftar Akun Baru
            </h1>

            <button
              onClick={handleGoogle}
              className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl border mb-5"
            >
              <Image
                src="/icons/Google_Icon.svg"
                alt="Google"
                width={18}
                height={18}
              />
              Daftar dengan Google
            </button>

            <div className="flex items-center gap-3 mb-5">
              <div
                className="flex-1 h-px"
                style={{ background: "var(--border)" }}
              />
              <span className="text-xs">atau</span>
              <div
                className="flex-1 h-px"
                style={{ background: "var(--border)" }}
              />
            </div>

            <form onSubmit={handleSubmit} className="space-y-3">
              <input
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-xl text-sm border"
                style={{
                  background: "var(--bg-input)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                }}
                required
                readOnly={!!emailFromUrl}
              />
              <input
                type="password"
                placeholder="Password (min. 6 karakter)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-xl text-sm border"
                style={{
                  background: "var(--bg-input)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                }}
              />
              <input
                type="password"
                placeholder="Konfirmasi Password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-xl text-sm border"
                style={{
                  background: "var(--bg-input)",
                  borderColor: "var(--border)",
                  color: "var(--text-primary)",
                }}
              />
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-3 px-4 rounded-xl font-medium text-sm"
                style={{
                  background: "var(--text-primary)",
                  color: "var(--bg-base)",
                }}
              >
                {isSubmitting ? "Memproses..." : "Daftar"}
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
}
