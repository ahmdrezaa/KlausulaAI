// src/app/dashboard/page.tsx
// Halaman Dashboard Chat Utama — Mockup 06 & 07
// Letakkan di: frontend/src/app/dashboard/page.tsx

"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import UploadModal from "@/components/modals/UploadModal";
import Image from "next/image";
import toast from "react-hot-toast";
import { useSearchParams } from "next/navigation";

interface ChatSession {
  id: string;
  project_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

interface Project {
  id: string;
  name: string;
  user_id: string;
  description?: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

interface Source {
  id: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  storage_path: string;
  status: string;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectIdFromUrl = searchParams.get("projectId");
  const sessionIdFromUrl = searchParams.get("sessionId");

  const { user, supabase, signOut } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sourcesPanelOpen, setSourcesPanelOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [allSources, setAllSources] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSession, setActiveSession] = useState<any>(null);
  const [isSending, setIsSending] = useState(false);

  // Load projects and active project
  useEffect(() => {
    if (!user) {
      router.push("/login");
      return;
    }
    loadProjectsAndSessions();
  }, [user]);

  const loadProjectsAndSessions = async () => {
    setLoading(true);
    try {
      // Load projects
      const { data: projectsData, error: projectsError } = await supabase
        .from("projects")
        .select("*")
        .eq("user_id", user?.id)
        .order("updated_at", { ascending: false });

      if (projectsError) throw projectsError;
      setProjects(projectsData || []);

      // Load all sessions
      const { data: sessionsData, error: sessionsError } = await supabase
        .from("chat_sessions")
        .select("*")
        .eq("user_id", user?.id)
        .order("updated_at", { ascending: false });

      if (sessionsError) throw sessionsError;
      setSessions(sessionsData || []);

      // Determine active project and session
      let targetProject: Project | null = null;
      let targetSession: ChatSession | null = null;

      if (projectIdFromUrl) {
        targetProject = projectsData?.find((p) => p.id === projectIdFromUrl);
        if (sessionIdFromUrl) {
          targetSession = sessionsData?.find((s) => s.id === sessionIdFromUrl);
        } else if (targetProject) {
          targetSession = sessionsData?.find(
            (s) => s.project_id === targetProject?.id,
          );
        }
      }

      if (targetProject) {
        setActiveProject(targetProject);
        if (targetSession) {
          setActiveSession(targetSession);
          await loadMessages(targetSession.id);
        } else if (targetProject.id) {
          await createNewSession(targetProject.id, undefined, false);
        }
        await loadSources(targetProject.id);
      }
    } catch (error: any) {
      console.error("Load error:", error);
      toast.error(error.message || "Gagal memuat data");
    } finally {
      setLoading(false);
    }
  };

  const loadMessages = async (sessionId: string) => {
    if (!sessionId) {
      console.warn("loadMessages called without sessionId");
      return;
    }

    const { data, error } = await supabase
      .from("chat_messages")
      .select("*")
      .eq("session_id", sessionId) // ← FILTER BY SESSION_ID
      .order("created_at", { ascending: true });

    if (error) {
      console.error("Load messages error:", error);
    } else {
      setMessages(data || []);
    }
  };

  const loadSources = async (projectId: string) => {
    const { data, error } = await supabase
      .from("documents") // ← project_sources → documents
      .select("*")
      .eq("project_id", projectId);

    if (error) {
      console.error("Load sources error:", error);
      toast.error("Gagal memuat sumber dokumen");
    } else {
      console.log("✅ Documents loaded:", data);
      setSources(data || []);

      // Set allSources berdasarkan status
      const allActive = data?.every((doc) => doc.status === "active") || false;
      setAllSources(allActive);
    }
  };

  const createNewSession = async (
    projectId: string,
    customTitle?: string,
    isManual = true,
  ) => {
    try {
      const { data, error } = await supabase
        .from("chat_sessions")
        .insert({
          project_id: projectId,
          user_id: user?.id,
          title: customTitle || "Obrolan Baru",
        })
        .select()
        .single();

      if (error) throw error;
      setSessions((prev) => [data, ...prev]);
      setActiveSession(data);
      setMessages([]);
      router.push(`/dashboard?projectId=${projectId}&sessionId=${data.id}`, {
        scroll: false,
      });

      // Hanya tampilkan toast jika manual (bukan auto-create)
      if (isManual) {
        toast.success("Obrolan baru dibuat");
      }

      return data;
    } catch (error: any) {
      if (isManual) {
        toast.error(error.message || "Gagal membuat obrolan baru");
      }
      return null;
    }
  };

  const deleteSession = async (sessionId: string, projectId: string) => {
    try {
      const { error } = await supabase
        .from("chat_sessions")
        .delete()
        .eq("id", sessionId);
      if (error) throw error;
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));

      if (activeSession?.id === sessionId) {
        const remainingSessions = sessions.filter((s) => s.id !== sessionId);
        const nextSession = remainingSessions.find(
          (s) => s.project_id === projectId,
        );
        if (nextSession) {
          setActiveSession(nextSession);
          await loadMessages(nextSession.id);
          router.push(
            `/dashboard?projectId=${projectId}&sessionId=${nextSession.id}`,
            { scroll: false },
          );
        } else {
          await createNewSession(projectId);
        }
      }
      toast.success("Obrolan dihapus");
    } catch (error: any) {
      toast.error(error.message || "Gagal menghapus obrolan");
    }
  };

  const renameSession = async (sessionId: string, newTitle: string) => {
    try {
      const { error } = await supabase
        .from("chat_sessions")
        .update({ title: newTitle, updated_at: new Date().toISOString() })
        .eq("id", sessionId);
      if (error) throw error;
      setSessions((prev) =>
        prev.map((s) => (s.id === sessionId ? { ...s, title: newTitle } : s)),
      );
      if (activeSession?.id === sessionId)
        setActiveSession({ ...activeSession, title: newTitle });
      toast.success("Nama obrolan diubah");
    } catch (error: any) {
      toast.error(error.message || "Gagal mengubah nama obrolan");
    }
  };

  const getSessionsForProject = (projectId: string) => {
    return sessions.filter((s) => s.project_id === projectId);
  };

  const handleSend = async () => {
    if (!input.trim() || !activeProject || !activeSession) return;

    const userInput = input;
    const tempId = Date.now().toString();

    const userMessage = {
      id: tempId,
      role: "user" as const,
      content: userInput,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsSending(true);

    try {
      // Save user message
      const { error: userMsgError } = await supabase
        .from("chat_messages")
        .insert({
          session_id: activeSession.id,
          project_id: activeProject.id,
          role: "user",
          content: userInput,
        });
      if (userMsgError) throw userMsgError;

      // Update session
      await supabase
        .from("chat_sessions")
        .update({ updated_at: new Date().toISOString() })
        .eq("id", activeSession.id);

      // Mock AI response
      setTimeout(async () => {
        const assistantMessage = {
          id: (Date.now() + 1).toString(),
          role: "assistant" as const,
          content:
            "Terima kasih atas pertanyaan Anda. Saya sedang menganalisis dokumen yang Anda unggah. Fitur ini akan segera terintegrasi dengan backend AI.",
        };

        setMessages((prev) => [...prev, assistantMessage]);

        // ✅ FIX: Tambahkan session_id untuk assistant message
        const { error: assistantError } = await supabase
          .from("chat_messages")
          .insert({
            session_id: activeSession.id, // ← HARUS ADA INI!
            project_id: activeProject.id,
            role: "assistant",
            content: assistantMessage.content,
          });

        if (assistantError) {
          console.error("Failed to save assistant message:", assistantError);
        }

        setIsSending(false);
      }, 1000);
    } catch (error) {
      console.error("Send message error:", error);
      toast.error("Gagal mengirim pesan");
      setMessages((prev) => prev.filter((m) => m.id !== tempId));
      setInput(userInput);
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleSource = async (id: string) => {
    const source = sources.find((s) => s.id === id);
    if (!source) {
      console.warn("Source not found:", id);
      return;
    }

    if (!activeProject) {
      toast.error("Project tidak aktif");
      return;
    }

    const newStatus = source.status === "active" ? "inactive" : "active";
    const projectId = activeProject.id;

    const oldStatus = source.status;

    setSources((prev) =>
      prev.map((s) => (s.id === id ? { ...s, status: newStatus } : s)),
    );

    try {
      const { error } = await supabase
        .from("documents")
        .update({
          status: newStatus,
        })
        .eq("id", id);

      if (error) throw error;

      setAllSources(
        sources.every((s) =>
          s.id === id ? newStatus === "active" : s.status === "active",
        ),
      );
    } catch (error) {
      console.error("Failed to update status:", error);

      setSources((prev) =>
        prev.map((s) => (s.id === id ? { ...s, status: oldStatus } : s)),
      );

      toast.error("Gagal mengupdate status sumber");
    }
  };

  const toggleAllSources = () => {
    const next = !allSources;
    setAllSources(next);
    const newStatus = next ? "active" : "inactive";

    setSources((prev) => prev.map((s) => ({ ...s, status: newStatus })));

    // Optional: Batch update ke Supabase
    const updates = sources.map((s) => ({
      id: s.id,
      status: newStatus,
    }));

    Promise.all(
      updates.map((update) =>
        supabase
          .from("documents")
          .update({ status: update.status })
          .eq("id", update.id),
      ),
    ).catch((error) => console.error("Failed to update statuses:", error));
  };

  const handleNewProject = () => router.push("/new-project");

  // FUNGSI LOGOUT
  const handleLogout = async () => {
    try {
      await signOut();
      toast.success("Berhasil logout");
      router.push("/login");
    } catch (error) {
      console.error("Logout error:", error);
      toast.error("Gagal logout. Silakan coba lagi.");
    }
  };

  // Jika masih loading, tampilkan loading state
  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: "var(--bg-base)" }}
      >
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-t-blue-500 rounded-full animate-spin mx-auto mb-4"></div>
          <p style={{ color: "var(--text-secondary)" }}>Memuat...</p>
        </div>
      </div>
    );
  }

  // Jika tidak ada user, jangan render dashboard (redirect sudah terjadi)
  if (!user) {
    return null;
  }

  return (
    <div
      className="flex h-screen overflow-hidden"
      style={{ background: "var(--bg-base)" }}
    >
      {/* ── Sidebar (left) ─────────────────────────────── */}
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-20 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`
          fixed md:relative z-30 md:z-auto
          flex flex-col h-full w-64 flex-shrink-0
          transition-transform duration-300
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        `}
        style={{
          background: "var(--bg-input)",
          // borderColor: "var(--border)",
        }}
      >
        {/* Logo */}
        <div
          className="flex items-center gap-2 px-5 py-4"
          // style={{ borderColor: "var(--border)" }}
        >
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

        {/* Actions */}
        <div
          className="px-4 py-3"
          // style={{ borderColor: "var(--border)" }}
        >
          <button
            onClick={handleNewProject}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-all hover:bg-white/5"
            style={{ color: "var(--text-secondary)" }}
          >
            <span
              className="text-lg leading-none"
              style={{ color: "var(--accent)" }}
            >
              <div
                className="flex items-center justify-center align-center h-6 w-6 rounded-full"
                style={{ background: "var(--bg-upload)" }}
              >
                +
              </div>
            </span>
            Tambah Projek
          </button>
          <button
            onClick={() => router.push("/projects")}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-all hover:bg-white/5"
            style={{ color: "var(--text-secondary)" }}
          >
            <SearchIcon />
            Cari Projek
          </button>
        </div>

        {/* Active Project & Its Sessions */}
        <div className="flex-1 overflow-y-auto px-4 py-3">
          <p
            className="text-xs font-semibold uppercase tracking-wider px-3 mb-2"
            style={{ color: "var(--text-muted)" }}
          >
            Obrolan
          </p>

          {activeProject ? (
            <div className="space-y-2">
              {/* New session button */}
              <button
                onClick={() => createNewSession(activeProject.id)}
                className="w-full align-center justify-center text-center px-3 py-2 rounded-lg text-sm transition-all hover:bg-white/5 flex items-center gap-2"
                style={{
                  color: "var(--text-primary)",
                  background: "var(--bg-upload)",
                }}
              >
                <span>+</span>
                <span>Obrolan Baru</span>
              </button>

              {/* Sessions list for active project */}
              <div className="space-y-0.5">
                {getSessionsForProject(activeProject.id).map((session) => (
                  <div key={session.id} className="group">
                    <button
                      onClick={() => {
                        setActiveSession(session);
                        loadMessages(session.id);
                        router.push(
                          `/dashboard?projectId=${activeProject.id}&sessionId=${session.id}`,
                          { scroll: false },
                        );
                      }}
                      className="w-full text-left px-3 py-2 rounded-lg text-md flex items-center justify-between hover:bg-white/5"
                      style={{
                        color: "var(--text-primary)",
                        background:
                          activeSession?.id === session.id
                            ? "rgba(201,139,122,0.12)"
                            : "transparent",
                        fontWeight:
                          activeSession?.id === session.id ? "600" : "400",
                      }}
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span className="truncate">{session.title}</span>
                      </div>
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            const newTitle = prompt(
                              "Masukkan nama baru:",
                              session.title,
                            );
                            if (newTitle?.trim())
                              renameSession(session.id, newTitle.trim());
                          }}
                          className="p-1 hover:bg-white/10 rounded"
                        >
                          ✎
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (confirm(`Hapus obrolan "${session.title}"?`)) {
                              deleteSession(session.id, activeProject.id);
                            }
                          }}
                          className="p-1 hover:bg-white/10 rounded text-red-400"
                        >
                          🗑
                        </button>
                      </div>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p
              className="text-sm text-center py-8"
              style={{ color: "var(--text-muted)" }}
            >
              Belum ada projek
            </p>
          )}
        </div>

        {/* Profile section */}
        <div
          className="mt-auto border-t py-2 px-2"
          style={{ borderColor: "var(--border)" }}
        >
          <div className="relative">
            <button
              onClick={() => setProfileMenuOpen(!profileMenuOpen)}
              className="w-full flex items-center gap-3 rounded-lg p-2 transition-all hover:bg-white/5"
            >
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                style={{ background: "var(--accent)" }}
              >
                <UserIcon width={16} height={16} stroke="var(--bg-base)" />
              </div>

              <div className="flex-1 text-left min-w-0">
                <p
                  className="text-sm font-medium truncate"
                  style={{ color: "var(--text-primary)" }}
                >
                  {user ? user.email : "User"} {/* ← pakai ternary */}
                </p>
              </div>

              <ChevronIcon
                width={16}
                height={16}
                stroke="var(--text-secondary)"
              />
            </button>

            {profileMenuOpen && (
              <div
                className="absolute bottom-full left-0 mb-2 w-full rounded-lg shadow-lg border overflow-hidden"
                style={{
                  background: "var(--bg-surface)",
                  borderColor: "var(--border)",
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  className="w-full text-left px-4 py-2.5 text-sm transition-all hover:bg-white/5 flex items-center gap-2"
                  style={{ color: "var(--text-primary)" }}
                  onClick={() => router.push("/settings")}
                >
                  <SettingsIcon width={14} height={14} />
                  Settings
                </button>
                <button
                  className="w-full text-left px-4 py-2.5 text-sm transition-all hover:bg-white/5 flex items-center gap-2"
                  style={{ color: "var(--text-primary)" }}
                >
                  <LanguageIcon width={14} height={14} />
                  Language &gt;
                </button>
                <button
                  className="w-full text-left px-4 py-2.5 text-sm transition-all hover:bg-white/5 flex items-center gap-2"
                  style={{ color: "var(--text-primary)" }}
                >
                  <HelpIcon width={14} height={14} />
                  Get help
                </button>
                <button
                  className="w-full text-left px-4 py-2.5 text-sm transition-all hover:bg-white/5 flex items-center gap-2"
                  style={{ color: "var(--text-primary)" }}
                >
                  <AppsIcon width={14} height={14} />
                  Get apps and extensions
                </button>
                <button
                  className="w-full text-left px-4 py-2.5 text-sm transition-all hover:bg-white/5 flex items-center gap-2"
                  style={{ color: "var(--text-primary)" }}
                >
                  <LearnIcon width={14} height={14} />
                  Learn more
                </button>
                <div className="h-px" style={{ background: "var(--border)" }} />
                <button
                  className="w-full text-left px-4 py-2.5 text-sm transition-all hover:bg-white/5 flex items-center gap-2"
                  style={{ color: "#ef4444" }}
                  onClick={handleLogout} // ← FUNGSI LOGOUT SUDAH TERHUBUNG
                >
                  <LogoutIcon width={14} height={14} />
                  Log out
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* ── Main area ──────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 w-full overflow-hidden">
        {/* Mobile topbar */}
        <div
          className="flex md:hidden items-center justify-between px-4 py-3"
          style={{
            // borderColor: "var(--border)",
            background: "var(--bg-surface)",
          }}
        >
          <button onClick={() => setSidebarOpen(true)}>
            <MenuIcon />
          </button>
          <span
            className="font-display text-base font-semibold"
            style={{ color: "var(--text-primary)" }}
          >
            {activeProject?.name || "Loading..."}
          </span>
          <button onClick={() => setSourcesPanelOpen(true)}>
            <FolderIcon />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden">
          {/* Chat area */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Project header */}
            <div className="px-6 md:px-8 pt-6 pb-4 hidden md:block">
              {/* TODO: Ambil data projek aktif dari Supabase */}
              <h2
                className="font-display text-5xl font-regular"
                style={{ color: "var(--accent)" }}
              >
                Bantuan Analisis
              </h2>
              <h2
                className="font-display text-3xl font-regular mb-2"
                style={{ color: "var(--text-primary)" }}
              >
                {activeProject?.name || "Loading..."}
              </h2>
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                Peninjauan klausul ganti rugi dan pengesampingan Pasal 1266
                KUHPerdata untuk kontrak vendor restoran.
              </p>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-6">
              {/* Welcome message (only if no messages) */}
              {messages.length === 0 && (
                <div className="text-center py-16">
                  <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                    Saat ini, saya juga telah tersambung dengan dokumen sumber
                    yang Anda unggah di sidebar kanan. Silakan ajukan pertanyaan
                    atau berikan instruksi khusus untuk memulai analisis.
                  </p>
                </div>
              )}

              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
            </div>

            {/* Input area */}
            <div className="px-4 md:px-8 py-4">
              <div
                className="flex items-center gap-3 rounded-xl border px-4"
                style={{
                  background: "var(--bg-input)",
                  borderColor: "var(--border)",
                }}
              >
                <textarea
                  rows={1}
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value);
                    // Auto-resize textarea
                    e.target.style.height = "auto";
                    e.target.style.height = e.target.scrollHeight + "px";
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder="Mulai mengetik"
                  className="flex-1 bg-transparent text-sm outline-none resize-none"
                  style={{
                    color: "var(--text-primary)",
                    lineHeight: "1.5",
                    padding: "12px 0",
                    height: "45px", // Set fixed height
                    maxHeight: "120px", // Optional: max height before scroll
                  }}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim()}
                  className="p-2 rounded-lg transition-all active:scale-90 flex-shrink-0 self-center"
                  style={{
                    background: input.trim()
                      ? "var(--accent)"
                      : "var(--bg-elevated)",
                    color: input.trim()
                      ? "var(--bg-base)"
                      : "var(--text-disabled)",
                  }}
                >
                  <SendIcon />
                </button>
              </div>
            </div>
          </div>

          {/* ── Sources panel (right) ─── Desktop */}
          <aside
            className="hidden md:flex w-96 flex-col"
            style={{
              background: "var(--bg-surface)",
              borderColor: "var(--border)",
            }}
          >
            <SourcesPanel
              sources={sources}
              allSources={allSources}
              onToggleAll={toggleAllSources}
              onToggleSource={toggleSource}
              onAddSource={() => setShowUpload(true)}
            />
          </aside>
        </div>
      </div>

      {/* ── Sources panel — Mobile drawer ────────────── */}
      {sourcesPanelOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          onClick={() => setSourcesPanelOpen(false)}
        >
          <div className="absolute inset-0 bg-black/60" />
          <div
            className="absolute right-0 top-0 h-full w-72 flex flex-col border-l"
            style={{
              background: "var(--bg-surface)",
              borderColor: "var(--border)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <SourcesPanel
              sources={sources}
              allSources={allSources}
              onToggleAll={toggleAllSources}
              onToggleSource={toggleSource}
              onAddSource={() => {
                setShowUpload(true);
                setSourcesPanelOpen(false);
              }}
            />
          </div>
        </div>
      )}

      {/* ── Upload Modal ─────────────────────────────── */}
      {showUpload && activeProject && (
        <UploadModal
          projectId={activeProject.id}
          onClose={() => setShowUpload(false)}
          onUploadComplete={() => {
            if (activeProject) {
              loadSources(activeProject.id);
            }
          }}
        />
      )}
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function MessageBubble({
  message,
}: {
  message: { id: string; role: "user" | "assistant"; content: string };
}) {
  const isUser = message.role === "user";

  const formattedContent = message.content.replace(/\n\s*\n/g, "\n\n");

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`${isUser ? "max-w-2xl" : "w-full"} rounded-2xl px-5 py-4 text-sm leading-relaxed whitespace-pre-wrap`}
        style={{
          background: isUser ? "var(--bg-card)" : "transparent",
          color: "var(--text-primary)",
          // border: isUser ? `1px solid var(--border)` : "none",
        }}
      >
        {message.content}

        {/* Action buttons (only for assistant) */}
        {!isUser && (
          <div className="flex items-center gap-3 mt-3">
            {[ThumbUpIcon, ThumbDownIcon, RefreshIcon, CopyIcon].map(
              (Icon, i) => (
                <button
                  key={i}
                  className="opacity-40 hover:opacity-80 transition-opacity"
                >
                  <Icon />
                </button>
              ),
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SourcesPanel({
  sources,
  allSources,
  onToggleAll,
  onToggleSource,
  onAddSource,
}: {
  sources: Source[]; // ← use the updated Source interface
  allSources: boolean;
  onToggleAll: () => void;
  onToggleSource: (id: string) => void;
  onAddSource: () => void;
}) {
  return (
    <div className="w-full h-full p-4 pl-0">
      <div
        className="rounded-2xl h-full overflow-hidden"
        style={{ background: "var(--bg-elevated)" }}
      >
        <div className="px-5 py-4" style={{ background: "var(--bg-elevated)" }}>
          <h3
            className="text-lg font-regular"
            style={{ color: "var(--text-primary)" }}
          >
            Sumber
          </h3>
        </div>

        <div className="px-4 space-y-3">
          <button
            onClick={onAddSource}
            className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-full border text-sm font-regular transition-all hover:opacity-80"
            style={{
              borderColor: "var(--border-light)",
              color: "var(--text-primary)",
              background: "var(--bg-upload)",
            }}
          >
            <PlusIcon />
            Tambahkan Sumber
          </button>

          <div className="h-px" style={{ background: "var(--border-light)" }} />

          <label
            className="flex items-center justify-between gap-3 cursor-pointer"
            onClick={onToggleAll}
          >
            <span
              className="text-xs font-regular"
              style={{ color: "var(--text-secondary)" }}
            >
              Pilih semua sumber ({sources.length})
            </span>
            <Checkbox checked={allSources} />
          </label>

          <div className="space-y-2">
            {sources.map((s) => (
              <label
                key={s.id}
                className="flex items-center justify-between gap-3 cursor-pointer group py-1 rounded-lg transition-all hover:bg-white/5"
                onClick={() => onToggleSource(s.id)}
              >
                <div className="flex-shrink-0">
                  <PdfIcon />
                </div>
                <div className="flex-1 min-w-0">
                  <p
                    className="text-sm truncate"
                    style={{ color: "var(--text-primary)" }}
                  >
                    {s.file_name}
                  </p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {(s.file_size_bytes / 1024).toFixed(1)} KB • {s.file_type}
                  </p>
                </div>
                <Checkbox checked={s.status === "active"} accent />
              </label>
            ))}
          </div>

          {sources.length === 0 && (
            <p
              className="text-sm text-center py-8"
              style={{ color: "var(--text-muted)" }}
            >
              Belum ada dokumen. Klik "Tambahkan Sumber" untuk upload file.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function PlusIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function UserIcon({ width = 20, height = 20, stroke = "currentColor" }) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 24 24"
      fill="none"
      stroke={stroke}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function ChevronIcon({ width = 20, height = 20, stroke = "currentColor" }) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 24 24"
      fill="none"
      stroke={stroke}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function LanguageIcon({ width = 20, height = 20, stroke = "currentColor" }) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 24 24"
      fill="none"
      stroke={stroke}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
    </svg>
  );
}

function HelpIcon({ width = 20, height = 20, stroke = "currentColor" }) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 24 24"
      fill="none"
      stroke={stroke}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function UpgradeIcon({ width = 20, height = 20, stroke = "currentColor" }) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 24 24"
      fill="none"
      stroke={stroke}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  );
}

function AppsIcon({ width = 20, height = 20, stroke = "currentColor" }) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 24 24"
      fill="none"
      stroke={stroke}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
    </svg>
  );
}

function LearnIcon({ width = 20, height = 20, stroke = "currentColor" }) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 24 24"
      fill="none"
      stroke={stroke}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  );
}

function LogoutIcon({ width = 20, height = 20, stroke = "currentColor" }) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 24 24"
      fill="none"
      stroke={stroke}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

function SettingsIcon({ ...props }: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}

function Checkbox({ checked, accent }: { checked: boolean; accent?: boolean }) {
  return (
    <div
      className="w-5 h-5 rounded flex-shrink-0 border flex items-center justify-center transition-all"
      style={{
        background: checked
          ? accent
            ? "var(--accent)"
            : "var(--accent)"
          : "transparent",
        borderColor: checked ? "var(--accent)" : "var(--border-light)",
      }}
    >
      {checked && (
        <svg width="11" height="9" viewBox="0 0 12 10" fill="none">
          <path
            d="M1 5l3.5 3.5L11 1"
            stroke="var(--bg-base)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </div>
  );
}

// ─── Icons ────────────────────────────────────────────────────────────────────
function ScaleIcon() {
  return (
    <svg
      width="24"
      height="24"
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

function SearchIcon() {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

function PdfIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--accent)"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--text-secondary)"
      strokeWidth="2"
      strokeLinecap="round"
    >
      <line x1="3" y1="6" x2="21" y2="6" />
      <line x1="3" y1="12" x2="21" y2="12" />
      <line x1="3" y1="18" x2="21" y2="18" />
    </svg>
  );
}

function FolderIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="var(--text-secondary)"
      strokeWidth="2"
      strokeLinecap="round"
    >
      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
    </svg>
  );
}

function ThumbUpIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3H14z" />
      <path d="M7 22H4a2 2 0 01-2-2v-7a2 2 0 012-2h3" />
    </svg>
  );
}

function ThumbDownIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M10 15v4a3 3 0 003 3l4-9V2H5.72a2 2 0 00-2 1.7l-1.38 9a2 2 0 002 2.3H10z" />
      <path d="M17 2h2.67A2.31 2.31 0 0122 4v7a2.31 2.31 0 01-2.33 2H17" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="1 4 1 10 7 10" />
      <path d="M3.51 15a9 9 0 102.13-9.36L1 10" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg
      width="15"
      height="15"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
    </svg>
  );
}
