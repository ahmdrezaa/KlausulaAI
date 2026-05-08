'use client'
import Link from 'next/link'
import { MessageSquare, BookOpen, History, Scale } from 'lucide-react'

const nav = [
  { href: '/dashboard/chat',           icon: MessageSquare, label: 'Chat' },
  { href: '/dashboard/knowledge-base', icon: BookOpen,      label: 'Knowledge Base' },
  { href: '/dashboard/history',        icon: History,       label: 'Riwayat' },
]

export default function Sidebar() {
  return (
    <aside className="w-64 h-full bg-card border-r border-border flex flex-col">
      <div className="p-6 flex items-center gap-3 border-b border-border">
        <Scale className="text-brand-400" size={24} />
        <span className="font-display font-bold text-lg">KlausulaAI</span>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {nav.map(({ href, icon: Icon, label }) => (
          <Link key={href} href={href}
            className="flex items-center gap-3 px-4 py-3 rounded-xl text-slate-400 hover:text-white hover:bg-brand-600/20 transition-colors text-sm font-medium">
            <Icon size={18} />
            {label}
          </Link>
        ))}
      </nav>
      <div className="p-4 border-t border-border text-xs text-slate-600 text-center">
        Kelompok 6 · FST Unair
      </div>
    </aside>
  )
}
