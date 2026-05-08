'use client'
import { useState, KeyboardEvent } from 'react'
import { Send } from 'lucide-react'

interface Props { onSend: (q: string) => void; disabled?: boolean }

export default function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState('')

  const submit = () => {
    if (!value.trim() || disabled) return
    onSend(value.trim())
    setValue('')
  }

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() }
  }

  return (
    <div className="p-4 border-t border-border">
      <div className="flex gap-3 items-end bg-card border border-border rounded-2xl px-4 py-3">
        <textarea
          rows={1}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Tanyakan tentang UU Indonesia..."
          className="flex-1 bg-transparent resize-none text-sm text-white placeholder-slate-500 outline-none"
        />
        <button onClick={submit} disabled={disabled || !value.trim()}
          className="p-2 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors">
          <Send size={16} />
        </button>
      </div>
      <p className="text-xs text-slate-600 text-center mt-2">
        KlausulaAI dapat membuat kesalahan. Verifikasi selalu pasal yang dirujuk.
      </p>
    </div>
  )
}
