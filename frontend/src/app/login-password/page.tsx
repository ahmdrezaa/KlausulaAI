// frontend/src/app/login-password/page.tsx
"use client";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";
import toast from "react-hot-toast";

export default function LoginPasswordPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const email = searchParams.get("email") || "";
  const { signIn } = useAuth();

  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Validasi email ada
  if (!email) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="mb-4">Email tidak ditemukan.</p>
          <Link href="/login" className="text-blue-500 underline">
            Kembali ke Login
          </Link>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!password) {
      toast.error("Silakan masukkan password Anda.");
      return;
    }

    setIsSubmitting(true);
    try {
      const { error } = await signIn(email, password);

      if (error) {
        if (error.message.includes("Invalid login credentials")) {
          toast.error("Password salah. Silakan coba lagi.");
        } else if (error.message.includes("Email not confirmed")) {
          toast.error("Email belum dikonfirmasi. Silakan cek inbox Anda.");
        } else {
          toast.error(error.message || "Login gagal. Silakan coba lagi.");
        }
        return;
      }

      toast.success("Login berhasil!");
      router.push("/dashboard");
    } catch (error) {
      console.error(error);
      toast.error("Gagal login. Silakan coba lagi.");
    } finally {
      setIsSubmitting(false);
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
          Kembali
        </Link>
      </nav>

      <main className="flex-1 flex items-center justify-center px-6 py-10">
        <div className="w-full max-w-xl">
          <div className="rounded-2xl p-8 border">
            <h1
              className="font-display text-5xl md:text-6xl font-regular text-center"
              style={{ color: "var(--text-primary)" }}
            >
              Login dengan Email
            </h1>
            <p
              className="text-center font-regular text-xl mb-10" style={{ color: 'var(--text-primary)' }}
            >
              Untuk akun {email}
            </p>

            <form onSubmit={handleSubmit} className="space-y-3">
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
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-3 px-4 rounded-xl font-medium text-sm"
                style={{
                  background: "var(--text-primary)",
                  color: "var(--bg-base)",
                }}
              >
                {isSubmitting ? "Memproses..." : "Login"}
              </button>
            </form>

            <p className="text-center text-xs mt-5">
              <Link
                href="/login"
                className="underline"
                style={{ color: "var(--accent)" }}
              >
                Gunakan email lain
              </Link>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
