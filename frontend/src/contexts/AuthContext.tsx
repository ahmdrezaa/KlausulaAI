// frontend/src/contexts/AuthContext.tsx
"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { User, Session, SupabaseClient } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";

type AuthContextType = {
  user: User | null;
  isLoading: boolean;
  supabase: SupabaseClient;
  signInWithGoogle: () => Promise<void>;
  signUp: (email: string, password: string) => Promise<{ error: any | null }>;
  signIn: (email: string, password: string) => Promise<{ error: any | null }>;
  checkEmailExists: (email: string) => Promise<boolean>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const supabase = createClient();

  useEffect(() => {
    // Cek session saat pertama kali load
    supabase.auth
      .getSession()
      .then(({ data: { session } }: { data: { session: Session | null } }) => {
        setUser(session?.user ?? null);
        setIsLoading(false);
      });

    // Listen untuk perubahan auth state
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(
      (_event: any, session: Session | null) => {
        setUser(session?.user ?? null);
        setIsLoading(false);
      }
    );

    return () => subscription.unsubscribe();
  }, [supabase]);

  const signInWithGoogle = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/dashboard`,
      },
    });
    if (error) throw error;
  };

  const signUp = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        // Nonaktifkan email confirmation
        emailRedirectTo: `${window.location.origin}/dashboard`,
      },
    });
    return { error };
  };

  const signIn = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    return { error };
  };

  const checkEmailExists = async (email: string): Promise<boolean> => {
    try {
      console.log(`🔍 Checking email: ${email}`);

      const response = await fetch("/api/check-email", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        console.error("API response not OK:", response.status);
        // Fallback: coba metode signUp (kurang akurat)
        return fallbackCheckEmail(email);
      }

      const data = await response.json();

      if (data.error) {
        console.error("API error:", data.error);
        return fallbackCheckEmail(email);
      }

      console.log(`✅ Email check result: ${data.exists ? "TERDAFTAR" : "BELUM TERDAFTAR"}`);
      return data.exists;
    } catch (error) {
      console.error("Error in checkEmailExists:", error);
      // Fallback jika API error
      return fallbackCheckEmail(email);
    }
  };

  // Fallback method menggunakan signUp (kurang akurat, tapi bisa dipakai)
  const fallbackCheckEmail = async (email: string): Promise<boolean> => {
    try {
      // Coba sign up dengan random password
      const randomPassword = Math.random().toString(36).slice(-12);
      const { error } = await supabase.auth.signUp({
        email,
        password: randomPassword,
      });

      // Jika error "already registered", berarti email terdaftar
      if (error?.message?.toLowerCase().includes("already registered")) {
        return true;
      }

      // Jika berhasil sign up (tidak error), berarti email baru
      // Tapi kita sudah buat akun dengan random password
      // Opsional: kita bisa hapus user ini
      return false;
    } catch (error) {
      console.error("Fallback check error:", error);
      return false;
    }
  };

  const signOut = async () => {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        supabase,
        signInWithGoogle,
        signUp,
        signIn,
        checkEmailExists,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}