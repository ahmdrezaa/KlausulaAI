"use client";
import { useState, useCallback, useRef, useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { streamChat, getSessionMessages } from "@/services/chatService";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{
    id: string;
    document_id?: string;
    metadata: Record<string, any>;
    rrf_score: number;
  }>;
}

interface UseChat {
  messages: ChatMessage[];
  loading: boolean;
  send: (query: string) => Promise<void>;
}

export function useChat(
  projectId?: string,
  sessionId?: string,
): UseChat {
  const { user, supabase } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesRef = useRef<ChatMessage[]>([]);

  useEffect(() => {
    if (user?.id && projectId && sessionId) {
      loadMessages();
    }
  }, [user?.id, projectId, sessionId]);

  const getToken = async (): Promise<string> => {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (!session?.access_token) throw new Error("Not authenticated");
    return session.access_token;
  };

  const loadMessages = useCallback(async () => {
    if (!projectId || !sessionId) return;
    try {
      const token = await getToken();
      const msgs = await getSessionMessages(projectId, sessionId, token);
      const formatted: ChatMessage[] = msgs.map((m: any) => ({
        id: m.id,
        role: m.role,
        content: m.content,
      }));
      setMessages(formatted);
      messagesRef.current = formatted;
    } catch (error) {
      console.error("Error loading messages:", error);
    }
  }, [projectId, sessionId]);

  const send = useCallback(
    async (query: string) => {
      if (!query.trim() || !projectId || !sessionId) return;

      setLoading(true);
      const userMsgId = `msg-${Date.now()}`;
      const assistantMsgId = `msg-${Date.now() + 1}`;

      const userMessage: ChatMessage = {
        id: userMsgId,
        role: "user",
        content: query,
      };

      const updated = [...messagesRef.current, userMessage];
      setMessages(updated);
      messagesRef.current = updated;

      const assistantMessage: ChatMessage = {
        id: assistantMsgId,
        role: "assistant",
        content: "",
      };

      const withAssistant = [...updated, assistantMessage];
      setMessages(withAssistant);
      messagesRef.current = withAssistant;

      try {
        const token = await getToken();
        await streamChat(projectId, sessionId, query, token, {
          onToken: (tok) => {
            messagesRef.current = messagesRef.current.map((m) =>
              m.id === assistantMsgId
                ? { ...m, content: m.content + tok }
                : m,
            );
            setMessages([...messagesRef.current]);
          },
          onSources: (sources) => {
            messagesRef.current = messagesRef.current.map((m) =>
              m.id === assistantMsgId ? { ...m, sources } : m,
            );
            setMessages([...messagesRef.current]);
          },
          onDone: () => {
            setLoading(false);
          },
          onError: (err) => {
            console.error("Stream error:", err);
            messagesRef.current = messagesRef.current.filter(
              (m) => m.id !== userMsgId && m.id !== assistantMsgId,
            );
            setMessages([...messagesRef.current]);
            setLoading(false);
          },
        });
      } catch (error) {
        console.error("Error sending message:", error);
        messagesRef.current = messagesRef.current.filter(
          (m) => m.id !== userMsgId && m.id !== assistantMsgId,
        );
        setMessages([...messagesRef.current]);
        setLoading(false);
      }
    },
    [projectId, sessionId],
  );

  return { messages, loading, send };
}
