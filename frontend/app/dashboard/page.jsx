// app/(dashboard)/dashboard/page.jsx
'use client'
import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import { useRouter } from 'next/navigation'

export default function Dashboard() {
  const [user, setUser] = useState(null)
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    getUser()
    getProjects()
  }, [])

  const getUser = async () => {
    const { data: { user } } = await supabase.auth.getUser()
    setUser(user)
  }

  const getProjects = async () => {
    const { data, error } = await supabase
      .from('projects')
      .select('*')
      .order('created_at', { ascending: false })
    
    if (!error) setProjects(data)
    setLoading(false)
  }

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.push('/login')
  }

  const createProject = async () => {
    const { data: { user } } = await supabase.auth.getUser()
    
    const { data, error } = await supabase
      .from('projects')
      .insert({
        user_id: user.id,
        title: 'Proyek Baru',
        description: '',
        status: 'active'
      })
      .select()
      .single()

    if (!error) {
      router.push(`/projects/${data.id}`)
    }
  }

  return (
    <div className="min-h-screen bg-[#1a0f0a]">
      
      {/* Navbar */}
      <nav className="border-b border-[#3d2a1e] px-8 py-4 flex justify-between items-center">
        <h1 className="text-white font-bold text-xl">⚖️ KlausulaAI</h1>
        <div className="flex items-center gap-4">
          <span className="text-gray-400 text-sm">
            {user?.email}
          </span>
          <button
            onClick={handleLogout}
            className="text-gray-400 hover:text-white text-sm"
          >
            Keluar
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-8 py-10">
        
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-white text-3xl font-bold">Dashboard</h2>
            <p className="text-gray-400 mt-1">Kelola proyek hukum Anda</p>
          </div>
          <button
            onClick={createProject}
            className="bg-[#c4783a] text-white px-6 py-3 rounded-lg 
                       font-medium hover:bg-[#a85e2a] transition"
          >
            + Proyek Baru
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          {[
            { label: 'Total Proyek', value: projects.length },
            { label: 'Aktif', value: projects.filter(p => p.status === 'active').length },
            { label: 'Selesai', value: projects.filter(p => p.status === 'done').length }
          ].map((stat) => (
            <div key={stat.label} 
                 className="bg-[#2a1a12] border border-[#3d2a1e] rounded-xl p-6">
              <p className="text-gray-400 text-sm">{stat.label}</p>
              <p className="text-white text-3xl font-bold mt-1">{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Projects List */}
        <div>
          <h3 className="text-white text-xl font-semibold mb-4">Proyek Terbaru</h3>
          
          {loading ? (
            <p className="text-gray-400">Memuat...</p>
          ) : projects.length === 0 ? (
            <div className="text-center py-20 border border-dashed border-[#3d2a1e] rounded-xl">
              <p className="text-gray-400 text-lg">Belum ada proyek</p>
              <p className="text-gray-500 text-sm mt-2">
                Klik "Proyek Baru" untuk memulai
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {projects.map((project) => (
                <div
                  key={project.id}
                  onClick={() => router.push(`/projects/${project.id}`)}
                  className="bg-[#2a1a12] border border-[#3d2a1e] rounded-xl p-6 
                             cursor-pointer hover:border-[#c4783a] transition"
                >
                  <h4 className="text-white font-semibold text-lg">{project.title}</h4>
                  <p className="text-gray-400 text-sm mt-1">{project.description}</p>
                  <div className="flex justify-between items-center mt-4">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      project.status === 'active' 
                        ? 'bg-green-900 text-green-400' 
                        : 'bg-gray-800 text-gray-400'
                    }`}>
                      {project.status}
                    </span>
                    <span className="text-gray-500 text-xs">
                      {new Date(project.created_at).toLocaleDateString('id-ID')}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}