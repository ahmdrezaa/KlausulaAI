'use client'
import { useState, useCallback, useRef, useEffect } from 'react'
import { useAuth } from '@/contexts/AuthContext'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{
    id: string
    document_id?: string
    metadata: Record<string, any>
    rrf_score: number
  }>
  timestamp: Date
}

interface UseChat {
  messages: ChatMessage[]
  loading: boolean
  send: (query: string) => Promise<void>
  clearHistory: () => Promise<void>
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function useChat(projectId?: string): UseChat {
  const { user, session } = useAuth()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const messagesRef = useRef<ChatMessage[]>([])

  // Load chat history on mount
  useEffect(() => {
    if (user?.id) {
      loadChatHistory()
    }
  }, [user?.id, projectId])

  const loadChatHistory = useCallback(async () => {
    if (!session?.access_token) return

    try {
      const params = new URLSearchParams()
      if (projectId) params.append('project_id', projectId)
      params.append('limit', '50')

      const response = await fetch(
        `${API_BASE_URL}/api/v1/chat/history?${params}`,
        {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }
      )

      if (!response.ok) throw new Error('Failed to load chat history')

      const data = await response.json()
      const formattedMessages: ChatMessage[] = (data.messages || []).map(
        (msg: any) => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          sources: msg.sources || [],
          timestamp: new Date(msg.created_at),
        })
      )

      setMessages(formattedMessages)
      messagesRef.current = formattedMessages
    } catch (error) {
      console.error('Error loading chat history:', error)
    }
  }, [session?.access_token, projectId])

  const send = useCallback(
    async (query: string) => {
      if (!query.trim() || !session?.access_token) return

      setLoading(true)
      const userMessageId = `msg-${Date.now()}`

      // Add user message optimistically
      const userMessage: ChatMessage = {
        id: userMessageId,
        role: 'user',
        content: query,
        timestamp: new Date(),
      }

      const updatedMessages = [...messagesRef.current, userMessage]
      setMessages(updatedMessages)
      messagesRef.current = updatedMessages

      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/chat/query`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            query: query.trim(),
            project_id: projectId || null,
          }),
        })

        if (!response.ok) {
          const error = await response.json()
          throw new Error(error.detail || 'Failed to get response')
        }

        const data = await response.json()

        const assistantMessage: ChatMessage = {
          id: `msg-${Date.now()}`,
          role: 'assistant',
          content: data.answer,
          sources: data.sources || [],
          timestamp: new Date(),
        }

        const finalMessages = [...updatedMessages, assistantMessage]
        setMessages(finalMessages)
        messagesRef.current = finalMessages
      } catch (error) {
        console.error('Error sending message:', error)
        // Remove user message on error
        const errorMessages = updatedMessages.slice(0, -1)
        setMessages(errorMessages)
        messagesRef.current = errorMessages

        // Add error message
        const errorMessage: ChatMessage = {
          id: `msg-${Date.now()}`,
          role: 'assistant',
          content:
            'Maaf, terjadi kesalahan. Silakan coba lagi atau periksa koneksi Anda.',
          timestamp: new Date(),
        }
        const messagesWithError = [...errorMessages, errorMessage]
        setMessages(messagesWithError)
        messagesRef.current = messagesWithError
      } finally {
        setLoading(false)
      }
    },
    [session?.access_token, projectId]
  )

  const clearHistory = useCallback(async () => {
    if (!session?.access_token) return

    try {
      const params = new URLSearchParams()
      if (projectId) params.append('project_id', projectId)

      const response = await fetch(
        `${API_BASE_URL}/api/v1/chat/history?${params}`,
        {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }
      )

      if (!response.ok) throw new Error('Failed to clear history')

      setMessages([])
      messagesRef.current = []
    } catch (error) {
      console.error('Error clearing history:', error)
    }
  }, [session?.access_token, projectId])

  return { messages, loading, send, clearHistory }
}
