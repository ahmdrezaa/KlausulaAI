'use client'
import { useChat } from '@/hooks/useChat'
import ChatInput from './ChatInput'
import MessageBubble from './MessageBubble'

export default function ChatWindow() {
  const { messages, loading, send } = useChat()

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center mt-20 text-slate-500">
            <p className="text-lg font-display font-semibold text-slate-300 mb-2">
              Tanyakan tentang regulasi Indonesia
            </p>
            <p className="text-sm">Contoh: "Apa syarat mendirikan PT menurut UU PT?"</p>
          </div>
        )}
        {messages.map(msg => <MessageBubble key={msg.id} message={msg} />)}
        {loading && (
          <div className="flex gap-2 items-center text-slate-400 text-sm">
            <span className="animate-pulse">KlausulaAI sedang menjawab...</span>
          </div>
        )}
      </div>
      <ChatInput onSend={send} disabled={loading} />
    </div>
  )
}
