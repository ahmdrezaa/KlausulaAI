const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function createSession(
  projectId: string,
  token: string,
  title?: string,
) {
  const response = await fetch(
    `${API_URL}/api/v1/projects/${projectId}/sessions`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ title: title || "Obrolan Baru" }),
    },
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Gagal membuat session");
  }

  return response.json();
}

export async function listSessions(projectId: string, token: string) {
  const response = await fetch(
    `${API_URL}/api/v1/projects/${projectId}/sessions`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );

  if (!response.ok) {
    throw new Error("Gagal memuat daftar obrolan");
  }

  const data = await response.json();
  return data.sessions;
}

export async function deleteSession(
  projectId: string,
  sessionId: string,
  token: string,
) {
  const response = await fetch(
    `${API_URL}/api/v1/projects/${projectId}/sessions/${sessionId}`,
    {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    },
  );

  if (!response.ok) {
    let detail = "Gagal menghapus obrolan";
    try {
      const error = await response.json();
      detail = error.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  return response.json();
}

export async function getSessionMessages(
  projectId: string,
  sessionId: string,
  token: string,
) {
  const response = await fetch(
    `${API_URL}/api/v1/projects/${projectId}/sessions/${sessionId}/messages`,
    {
      headers: { Authorization: `Bearer ${token}` },
    },
  );

  if (!response.ok) {
    throw new Error("Gagal memuat pesan");
  }

  const data = await response.json();
  return data.messages;
}

export async function streamChat(
  projectId: string,
  sessionId: string,
  message: string,
  token: string,
  callbacks: {
    onToken: (token: string) => void;
    onSources: (sources: any[]) => void;
    onDone: () => void;
    onError: (error: string) => void;
  },
) {
  const response = await fetch(
    `${API_URL}/api/v1/projects/${projectId}/sessions/${sessionId}/chat`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message }),
    },
  );

  if (!response.ok) {
    let detail = "Gagal mengirim pesan";
    try {
      const error = await response.json();
      detail = error.detail || detail;
    } catch {}
    callbacks.onError(detail);
    return;
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith("data: ")) continue;

      try {
        const event = JSON.parse(line.slice(6));

        if (event.type === "sources") {
          callbacks.onSources(event.data);
        } else if (event.type === "token") {
          callbacks.onToken(event.data);
        } else if (event.type === "done") {
          callbacks.onDone();
        } else if (event.type === "error") {
          callbacks.onError(event.data);
        }
      } catch (e) {
        console.warn("[chatService] failed to parse SSE line:", line, e);
      }
    }
  }
}
