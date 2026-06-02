// src/app/projects/page.tsx
// Halaman Daftar Projek — Dengan icon, menu dropdown, dan edit modal

"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { useAuth } from "@/contexts/AuthContext";
import toast from "react-hot-toast";

// Pilihan icon untuk projek
const ICON_OPTIONS = [
  { id: "scale", icon: ScaleIcon, name: "Timbangan" },
  { id: "document", icon: DocumentIcon, name: "Dokumen" },
  { id: "folder", icon: FolderSmallIcon, name: "Folder" },
  { id: "star", icon: StarIcon, name: "Bintang" },
  { id: "heart", icon: HeartIcon, name: "Hati" },
  { id: "book", icon: BookIcon, name: "Buku" },
  { id: "gavel", icon: GavelIcon, name: "Palu Hakim" },
  { id: "law", icon: LawIcon, name: "Kitab Hukum" },
];

// Dummy data untuk preview projek
// TODO: Ganti dengan data real dari Supabase
const DUMMY_PROJECTS = [
  {
    id: "1",
    name: "Clustering Indonesian E-Commerce...",
    updatedAt: "May 7, 2026",
    sourceCount: 9,
    isPinned: true,
    iconId: "book",
    description: "Analisis clustering e-commerce Indonesia menggunakan metode K-Means",
  },
  {
    id: "2",
    name: "Comparative Clustering Analysis",
    updatedAt: "Apr 27, 2026",
    sourceCount: 1,
    isPinned: false,
    iconId: "document",
    description: "Perbandingan berbagai metode clustering untuk data e-commerce",
  },
  {
    id: "3",
    name: "Sengketa Lahan Blok A",
    updatedAt: "Apr 20, 2026",
    sourceCount: 5,
    isPinned: true,
    iconId: "folder",
    description: "Analisis hukum kepemilikan tanah dan sengketa batas wilayah",
  },
  {
    id: "4",
    name: "Kontrak Vendor Restoran",
    updatedAt: "Apr 15, 2026",
    sourceCount: 3,
    isPinned: false,
    iconId: "document",
    description: "Peninjauan klausul ganti rugi dan pembatalan sepihak",
  },
  {
    id: "5",
    name: "UU Cipta Kerja Omnibus Law",
    updatedAt: "Apr 10, 2026",
    sourceCount: 12,
    isPinned: false,
    iconId: "folder",
    description: "Analisis dampak UU Cipta Kerja terhadap UMKM",
  },
  {
    id: "6",
    name: "Perlindungan Data Pribadi",
    updatedAt: "Apr 5, 2026",
    sourceCount: 7,
    isPinned: false,
    iconId: "book",
    description: "Kepatuhan terhadap UU PDP untuk startup tech",
  },
];

// Type untuk project
type Project = {
  id: string;
  name: string;
  updatedAt: string;
  sourceCount: number;
  isPinned: boolean;
  iconId: string;
  description: string;
};

export default function ProjectsPage() {
  const router = useRouter();
  const { supabase, user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [showPinnedOnly, setShowPinnedOnly] = useState(false);
  
  // Edit modal state
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editIconId, setEditIconId] = useState("");
  
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);

  // Load projects from Supabase
  useEffect(() => {
    if (!user) {
      router.push("/login");
      return;
    }
    loadProjects();
  }, [user]);

  const loadProjects = async () => {
    setLoading(true);
    try {
      const { data, error } = await supabase
        .from("projects")
        .select("*")
        .eq("user_id", user?.id)
        .order("is_pinned", { ascending: false })
        .order("updated_at", { ascending: false });

      if (error) throw error;

      const formattedProjects: Project[] = (data || []).map((p) => ({
        id: p.id,
        name: p.name,
        updatedAt: new Date(p.updated_at).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
        }),
        sourceCount: 0, // TODO: hitung dari project_sources
        isPinned: p.is_pinned || false,
        iconId: p.icon_id || "scale",
        description: p.description || "",
      }));

      setProjects(formattedProjects);
    } catch (error: any) {
      console.error("Load projects error:", error);
      toast.error(error.message || "Gagal memuat projek");
    } finally {
      setLoading(false);
    }
  };

  const handleNewProject = () => router.push("/new-project");
  const handleProjectClick = (projectId: string) => {
    router.push(`/dashboard?projectId=${projectId}`);
  };

  const handleOpenEditModal = (project: Project) => {
    setEditingProject(project);
    setEditName(project.name);
    setEditDescription(project.description);
    setEditIconId(project.iconId);
    setOpenMenuId(null);
  };

  const handleSaveEdit = async () => {
    if (editingProject && editName.trim()) {
      try {
        const { error } = await supabase
          .from("projects")
          .update({
            name: editName.trim(),
            description: editDescription,
            icon_id: editIconId,
            updated_at: new Date().toISOString(),
          })
          .eq("id", editingProject.id);

        if (error) throw error;

        setProjects((prev) =>
          prev.map((p) =>
            p.id === editingProject.id
              ? {
                  ...p,
                  name: editName.trim(),
                  description: editDescription,
                  iconId: editIconId,
                }
              : p
          )
        );
        toast.success("Projek berhasil diupdate");
        setEditingProject(null);
      } catch (error: any) {
        console.error("Update project error:", error);
        toast.error(error.message || "Gagal mengupdate projek");
      }
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    try {
      const { error } = await supabase
        .from("projects")
        .delete()
        .eq("id", projectId);

      if (error) throw error;

      setProjects((prev) => prev.filter((p) => p.id !== projectId));
      toast.success("Projek berhasil dihapus");
      setOpenMenuId(null);
    } catch (error: any) {
      console.error("Delete project error:", error);
      toast.error(error.message || "Gagal menghapus projek");
    }
  };

  const handleTogglePin = async (projectId: string) => {
    const project = projects.find((p) => p.id === projectId);
    if (!project) return;

    try {
      const { error } = await supabase
        .from("projects")
        .update({ is_pinned: !project.isPinned })
        .eq("id", projectId);

      if (error) throw error;

      setProjects((prev) =>
        prev.map((p) =>
          p.id === projectId ? { ...p, isPinned: !p.isPinned } : p
        )
      );
      setOpenMenuId(null);
    } catch (error: any) {
      console.error("Toggle pin error:", error);
      toast.error(error.message || "Gagal mengubah pin");
    }
  };

  const filteredProjects = projects.filter((p) => {
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesPinned = showPinnedOnly ? p.isPinned : true;
    return matchesSearch && matchesPinned;
  });

  const pinnedProjects = filteredProjects.filter((p) => p.isPinned);
  const unpinnedProjects = filteredProjects.filter((p) => !p.isPinned);

  // Close dropdown when clicking outside
  const handleClickOutside = () => {
    if (openMenuId) setOpenMenuId(null);
  };

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--bg-base)" }}
      onClick={handleClickOutside}
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

        <div className="flex items-center gap-4">
          <div className="relative">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search projects..."
              className="pl-9 pr-4 py-[5px] rounded-lg text-sm outline-none transition-all border focus:border-[var(--accent)] w-64"
              style={{
                background: "var(--bg-input)",
                borderColor: "var(--border)",
                color: "var(--text-primary)",
              }}
            />
          </div>

          <button
            className="p-1 rounded-lg transition-all hover:bg-white/5"
            onClick={() => router.push("/settings")}
          >
            <SettingsIcon />
          </button>
        </div>
      </nav>


      <main className="flex-1 px-6 md:px-10 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1
              className="font-display text-5xl font-regular mb-1"
              style={{ color: "var(--text-primary)" }}
            >
              All Projects
            </h1>
            <p className="text-xl" style={{ color: "var(--text-secondary)" }}>
              Kelola semua projek analisis hukum Anda
            </p>
          </div>
          <button
            onClick={handleNewProject}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border font-medium text-sm transition-all hover:opacity-80 active:scale-[0.97]"
            style={{
              background: "var(--text-primary)",
              borderColor: "var(--text-primary)",
              color: "var(--bg-base)",
            }}
          >
            <PlusIcon />
            Buat Projek Baru
          </button>
        </div>

        <div className="flex items-center justify-end mb-6">
          <label
            className="flex items-center gap-2 cursor-pointer text-sm"
            style={{ color: "var(--text-secondary)" }}
            onClick={() => setShowPinnedOnly(!showPinnedOnly)}
          >
            <Checkbox checked={showPinnedOnly} accent />
            Show pinned only
          </label>
        </div>

        {filteredProjects.length === 0 ? (
          <div
            className="flex flex-col items-center justify-center py-16 rounded-2xl border border-dashed"
            style={{ borderColor: "var(--border)", background: "var(--bg-card)" }}
          >
            <FolderIcon width={48} height={48} stroke="var(--text-muted)" />
            <p className="mt-3 text-sm" style={{ color: "var(--text-muted)" }}>
              No projects found
            </p>
            <button
              onClick={handleNewProject}
              className="mt-4 text-sm hover:underline"
              style={{ color: "var(--accent)" }}
            >
              Create your first project
            </button>
          </div>
        ) : (
          <>
            {showPinnedOnly && pinnedProjects.length > 0 && (
              <div className="mb-10">
                <h3
                  className="text-sm font-medium mb-4"
                  style={{ color: "var(--text-secondary)" }}
                >
                  Pinned
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {pinnedProjects.map((project) => (
                    <ProjectCard
                      key={project.id}
                      project={project}
                      onProjectClick={handleProjectClick}
                      onOpenMenu={setOpenMenuId}
                      isMenuOpen={openMenuId === project.id}
                      onEdit={handleOpenEditModal}
                      onDelete={handleDeleteProject}
                      onTogglePin={handleTogglePin}
                    />
                  ))}
                </div>
              </div>
            )}

            {(showPinnedOnly ? unpinnedProjects : filteredProjects).length > 0 && (
              <div>
                {showPinnedOnly && unpinnedProjects.length > 0 && (
                  <h3
                    className="text-sm font-medium mb-4"
                    style={{ color: "var(--text-secondary)" }}
                  >
                    All projects
                  </h3>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {(showPinnedOnly ? unpinnedProjects : filteredProjects).map((project) => (
                    <ProjectCard
                      key={project.id}
                      project={project}
                      onProjectClick={handleProjectClick}
                      onOpenMenu={setOpenMenuId}
                      isMenuOpen={openMenuId === project.id}
                      onEdit={handleOpenEditModal}
                      onDelete={handleDeleteProject}
                      onTogglePin={handleTogglePin}
                    />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* Edit Modal */}
      {editingProject && (
        <EditProjectModal
          name={editName}
          description={editDescription}
          iconId={editIconId}
          onNameChange={setEditName}
          onDescriptionChange={setEditDescription}
          onIconChange={setEditIconId}
          onSave={handleSaveEdit}
          onClose={() => setEditingProject(null)}
        />
      )}
    </div>
  );
}

// Project Card Component
function ProjectCard({
  project,
  onProjectClick,
  onOpenMenu,
  isMenuOpen,
  onEdit,
  onDelete,
  onTogglePin,
}: {
  project: Project;
  onProjectClick: (id: string) => void;
  onOpenMenu: (id: string | null) => void;
  isMenuOpen: boolean;
  onEdit: (project: Project) => void;
  onDelete: (id: string) => void;
  onTogglePin: (id: string) => void;
}) {
  const getIconComponent = (iconId: string) => {
    const option = ICON_OPTIONS.find(opt => opt.id === iconId);
    return option?.icon || ScaleIcon;
  };
  
  const IconComponent = getIconComponent(project.iconId);

  return (
    <div
      className="group rounded-xl cursor-pointer transition-all hover:scale-[1.02] active:scale-[0.98] relative h-full"
      style={{
        background: "var(--bg-card)",
      }}
    >
      <div className="p-3 flex flex-col h-full" onClick={() => onProjectClick(project.id)}>
        {/* Baris 1: Icon + Menu button (posisi tetap di atas) */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center justify-start h-16">
            <IconComponent width={56} height={56} stroke="var(--accent)" />
          </div>
          
          {/* Menu button */}
          <button
            className="p-1.5 rounded-md transition-all hover:bg-white/10"
            style={{ color: "var(--text-secondary)" }}
            onClick={(e) => {
              e.stopPropagation();
              onOpenMenu(isMenuOpen ? null : project.id);
            }}
          >
            <MoreIcon width={24} height={24} />
          </button>
        </div>

        {/* Baris 2: Project name (selalu di posisi ini, dengan min-height) */}
        <div className="flex-1 flex flex-col justify-end min-h-[4rem]">
          <h3
            className="text-2xl font-medium line-clamp-2"
            style={{ color: "var(--text-primary)" }}
          >
            {project.name}
          </h3>
        </div>

        {/* Baris 3: Metadata (di bawah) */}
        <div className="flex items-center gap-1 text-md mt-[2px]" style={{ color: "var(--text-muted)" }}>
          <span>{project.updatedAt}</span>
          <span>•</span>
          <span>{project.sourceCount} sources</span>
        </div>
      </div>

      {/* Dropdown Menu */}
      {isMenuOpen && (
        <div
          className="absolute right-2 top-12 z-10 w-40 rounded-lg shadow-lg border overflow-hidden"
          style={{
            background: "var(--bg-surface)",
            borderColor: "var(--border)",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            className="w-full text-left px-4 py-2 text-sm transition-all hover:bg-white/5"
            style={{ color: "var(--text-primary)" }}
            onClick={() => onEdit(project)}
          >
            Edit title
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm transition-all hover:bg-white/5"
            style={{ color: "var(--text-primary)" }}
            onClick={() => onTogglePin(project.id)}
          >
            {project.isPinned ? "Unpin from top" : "Pin to top"}
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm transition-all hover:bg-white/5"
            style={{ color: "#ef4444" }}
            onClick={() => onDelete(project.id)}
          >
            Delete
          </button>
        </div>
      )}
    </div>
  );
}

// Edit Project Modal
function EditProjectModal({
  name,
  description,
  iconId,
  onNameChange,
  onDescriptionChange,
  onIconChange,
  onSave,
  onClose,
}: {
  name: string;
  description: string;
  iconId: string;
  onNameChange: (val: string) => void;
  onDescriptionChange: (val: string) => void;
  onIconChange: (val: string) => void;
  onSave: () => void;
  onClose: () => void;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl overflow-hidden"
        style={{ background: "var(--bg-surface)", borderColor: "var(--border)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b" style={{ borderColor: "var(--border)" }}>
          <h2
            className="text-xl font-semibold"
            style={{ color: "var(--text-primary)" }}
          >
            Edit Notebook
          </h2>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">
          {/* Icon selection */}
          <div>
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: "var(--text-secondary)" }}
            >
              Icon
            </label>
            <div className="flex flex-wrap gap-2">
              {ICON_OPTIONS.map((icon) => {
                const IconComp = icon.icon;
                const isSelected = iconId === icon.id;
                return (
                  <button
                    key={icon.id}
                    className="p-2 rounded-lg transition-all"
                    style={{
                      background: isSelected ? "var(--accent)" : "var(--bg-elevated)",
                      color: isSelected ? "var(--bg-base)" : "var(--text-secondary)",
                    }}
                    onClick={() => onIconChange(icon.id)}
                  >
                    <IconComp width={20} height={20} stroke={isSelected ? "var(--bg-base)" : "currentColor"} />
                  </button>
                );
              })}
            </div>
          </div>

          {/* Notebook Title */}
          <div>
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: "var(--text-secondary)" }}
            >
              Notebook Title *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => onNameChange(e.target.value)}
              placeholder="Enter notebook title"
              className="w-full px-4 py-2.5 rounded-xl text-sm outline-none transition-all border focus:border-[var(--accent)]"
              style={{
                background: "var(--bg-input)",
                borderColor: "var(--border)",
                color: "var(--text-primary)",
              }}
              autoFocus
            />
          </div>

          {/* Description */}
          <div>
            <label
              className="block text-sm font-medium mb-2"
              style={{ color: "var(--text-secondary)" }}
            >
              Description (optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => onDescriptionChange(e.target.value)}
              placeholder="Add a description..."
              rows={3}
              className="w-full px-4 py-2.5 rounded-xl text-sm outline-none transition-all border focus:border-[var(--accent)] resize-none"
              style={{
                background: "var(--bg-input)",
                borderColor: "var(--border)",
                color: "var(--text-primary)",
              }}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t" style={{ borderColor: "var(--border)" }}>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm transition-all hover:bg-white/5"
            style={{ color: "var(--text-secondary)" }}
          >
            Cancel
          </button>
          <button
            onClick={onSave}
            disabled={!name.trim()}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-all active:scale-[0.97]"
            style={{
              background: name.trim() ? "var(--accent)" : "var(--bg-elevated)",
              color: name.trim() ? "var(--bg-base)" : "var(--text-disabled)",
              cursor: name.trim() ? "pointer" : "not-allowed",
            }}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

// ============ Icons ============
function SearchIcon({ className = "", ...props }: React.SVGProps<SVGSVGElement>) {
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
      className={className}
      {...props}
    >
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
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

function PlusIcon({ ...props }: React.SVGProps<SVGSVGElement>) {
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
      {...props}
    >
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function MoreIcon({ ...props }: React.SVGProps<SVGSVGElement>) {
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
      {...props}
    >
      <circle cx="12" cy="12" r="1" />
      <circle cx="19" cy="12" r="1" />
      <circle cx="5" cy="12" r="1" />
    </svg>
  );
}

function FolderIcon({ ...props }: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    </svg>
  );
}

// Icon untuk project
function ScaleIcon({ ...props }: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M12 3v1M3 9h18M7 9l-3 6a3 3 0 006 0L7 9zM17 9l-3 6a3 3 0 006 0L17 9zM12 4l8 5M12 4L4 9M12 21v-6M9 21h6" />
    </svg>
  );
}

function DocumentIcon({ ...props }: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
    </svg>
  );
}

function FolderSmallIcon({ ...props }: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
    </svg>
  );
}

function StarIcon({ ...props }: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  );
}

function HeartIcon({ ...props }: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  );
}

function BookIcon({ ...props }: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}

function GavelIcon({ ...props }: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="M6 7L18 5" />
      <path d="M10 4L8 12" />
      <path d="M14 3L12 11" />
      <path d="M5 15L19 13" />
      <path d="M4 19L20 17" />
    </svg>
  );
}

function LawIcon({ ...props }: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="16" />
      <line x1="8" y1="12" x2="16" y2="12" />
    </svg>
  );
}

function Checkbox({ checked, accent }: { checked: boolean; accent?: boolean }) {
  return (
    <div
      className="w-4 h-4 rounded flex-shrink-0 border flex items-center justify-center transition-all"
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
        <svg width="9" height="7" viewBox="0 0 12 10" fill="none">
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