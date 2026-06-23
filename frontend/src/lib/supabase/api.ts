// frontend/src/lib/supabase/api.ts

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============================================================
// TYPES
// ============================================================

export interface ChatSource {
  id: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  storage_path: string;
  status: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ChatHistoryResponse {
  messages: ChatMessage[];
  session_id: string;
  project_id: string;
}

// ============================================================
// CHAT API
// ============================================================

/**
 * Send a chat message with SSE streaming response
 */
export async function sendChatMessage(
  query: string,
  projectId: string,
  sessionId: string,
  token: string,
  onToken: (token: string) => void,
  onComplete: (messageId: string) => void,
  onError: (error: string) => void,
  onSources?: (sources: ChatSource[]) => void
) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/projects/${projectId}/chat`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: query,
          session_id: sessionId,
        }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to send message');
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('No response body');
    }

    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;

      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));

            switch (data.type) {
              case 'token':
                onToken(data.data);
                break;

              case 'sources':
                if (onSources) {
                  onSources(data.data || []);
                }
                break;

              case 'done':
                onComplete(data.message_id || Date.now().toString());
                break;

              case 'error':
                onError(data.data || 'Unknown error');
                break;

              default:
                console.log('Unknown SSE event type:', data.type, data);
            }
          } catch (e) {
            console.error('Failed to parse SSE data:', e, 'Line:', line);
          }
        }
      }
    }
  } catch (error: any) {
    onError(error.message || 'Failed to send message');
  }
}

/**
 * Get chat history for a session
 */
export async function getChatHistory(
  sessionId: string,
  token: string
): Promise<ChatHistoryResponse> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/chat/history/${sessionId}`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch chat history');
    }

    return response.json();
  } catch (error: any) {
    console.error('Get chat history error:', error);
    // Fallback: return empty history
    return {
      messages: [],
      session_id: sessionId,
      project_id: '',
    };
  }
}

/**
 * Clear chat history for a session
 */
export async function clearChatHistory(
  sessionId: string,
  token: string
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/chat/history/${sessionId}`,
      {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to clear chat history');
    }

    return response.json();
  } catch (error: any) {
    console.error('Clear chat history error:', error);
    return {
      success: false,
      message: error.message || 'Failed to clear chat history',
    };
  }
}

// ============================================================
// SOURCES API
// ============================================================

/**
 * Get all sources for a project
 */
export async function getProjectSources(
  projectId: string,
  token: string
): Promise<ChatSource[]> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/projects/${projectId}/sources`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch sources');
    }

    const data = await response.json();
    return data.sources || [];
  } catch (error: any) {
    console.error('Get sources error:', error);
    return [];
  }
}

/**
 * Delete a source from a project
 */
export async function deleteProjectSource(
  projectId: string,
  sourceId: string,
  token: string
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/projects/${projectId}/sources/${sourceId}`,
      {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete source');
    }

    return response.json();
  } catch (error: any) {
    console.error('Delete source error:', error);
    return {
      success: false,
      message: error.message || 'Failed to delete source',
    };
  }
}

// ============================================================
// PROJECT API
// ============================================================

/**
 * Get all projects for the current user
 */
export async function getUserProjects(
  token: string
): Promise<any[]> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/projects`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch projects');
    }

    const data = await response.json();
    return data.projects || [];
  } catch (error: any) {
    console.error('Get projects error:', error);
    return [];
  }
}

/**
 * Create a new project
 */
export async function createProject(
  name: string,
  token: string,
  description?: string,
  masterPrompt?: string
): Promise<any> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/projects`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name,
          description,
          master_prompt: masterPrompt,
        }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create project');
    }

    return response.json();
  } catch (error: any) {
    console.error('Create project error:', error);
    throw error;
  }
}

/**
 * Delete a project
 */
export async function deleteProject(
  projectId: string,
  token: string
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/projects/${projectId}`,
      {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete project');
    }

    return response.json();
  } catch (error: any) {
    console.error('Delete project error:', error);
    return {
      success: false,
      message: error.message || 'Failed to delete project',
    };
  }
}

// ============================================================
// SESSION API
// ============================================================

/**
 * Get all chat sessions for a project
 */
export async function getProjectSessions(
  projectId: string,
  token: string
): Promise<any[]> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/projects/${projectId}/sessions`,
      {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch sessions');
    }

    const data = await response.json();
    return data.sessions || [];
  } catch (error: any) {
    console.error('Get sessions error:', error);
    return [];
  }
}

/**
 * Create a new chat session
 */
export async function createChatSession(
  projectId: string,
  title: string,
  token: string
): Promise<any> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/projects/${projectId}/sessions`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ title }),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create session');
    }

    return response.json();
  } catch (error: any) {
    console.error('Create session error:', error);
    throw error;
  }
}

/**
 * Delete a chat session
 */
export async function deleteChatSession(
  projectId: string,
  sessionId: string,
  token: string
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/v1/projects/${projectId}/sessions/${sessionId}`,
      {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete session');
    }

    return response.json();
  } catch (error: any) {
    console.error('Delete session error:', error);
    return {
      success: false,
      message: error.message || 'Failed to delete session',
    };
  }
}

// ============================================================
// UPLOAD API
// ============================================================

/**
 * Upload files to a project
 */
export async function uploadFiles(
  projectId: string,
  files: File[],
  token: string,
  onProgress?: (progress: number) => void
): Promise<{ files: any[]; message: string }> {
  try {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const response = await fetch(
      `${API_BASE_URL}/api/v1/projects/${projectId}/upload`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to upload files');
    }

    return response.json();
  } catch (error: any) {
    console.error('Upload files error:', error);
    throw error;
  }
}

// ============================================================
// EXPORTS
// ============================================================

// Default export untuk kemudahan
export default {
  // Chat
  sendChatMessage,
  getChatHistory,
  clearChatHistory,

  // Sources
  getProjectSources,
  deleteProjectSource,

  // Projects
  getUserProjects,
  createProject,
  deleteProject,

  // Sessions
  getProjectSessions,
  createChatSession,
  deleteChatSession,

  // Upload
  uploadFiles,
};