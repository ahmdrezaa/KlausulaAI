import type { Message } from '@/types'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-2xl rounded-2xl px-5 py-3 text-sm leading-relaxed ${
        isUser ? 'bg-brand-600 text-white' : 'bg-card border border-border text-slate-200'
      }`}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 pt-3 border-t border-brand-400/20 space-y-1">
            <p className="text-xs font-semibold text-brand-300 mb-1">📌 Sitasi Pasal</p>
            {message.citations.map((c, i) => (
              <div key={i} className="text-xs text-slate-400 bg-surface/50 rounded-lg px-3 py-2">
                <span className="font-medium text-brand-400">{c.pasal}</span> — {c.uu}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
