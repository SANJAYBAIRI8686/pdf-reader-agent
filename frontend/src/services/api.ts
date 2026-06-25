const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

interface RequestOptions extends RequestInit {
  token?: string;
}

/**
 * Standard HTTP request helper appending auth headers dynamically.
 */
async function apiRequest(endpoint: string, options: RequestOptions = {}) {
  const headers = new Headers(options.headers || {});
  
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }
  
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    let detail = "Request failed.";
    try {
      const parsed = JSON.parse(errorText);
      detail = parsed.detail || detail;
    } catch {
      detail = errorText || detail;
    }
    throw new Error(detail);
  }
  
  return response.json();
}

export const api = {
  // --- Auth API ---
  register: (body: any) => 
    apiRequest("/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }),
    
  login: (formData: URLSearchParams) =>
    apiRequest("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData.toString()
    }),
    
  getMe: (token: string) =>
    apiRequest("/auth/me", {
      method: "GET",
      token
    }),

  // --- Documents API ---
  listDocuments: (token: string) =>
    apiRequest("/documents/", {
      method: "GET",
      token
    }),
    
  uploadDocument: (file: File, token: string) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiRequest("/documents/upload", {
      method: "POST",
      token,
      body: formData
      // Note: Do NOT set Content-Type header; browser will auto-append multipart boundary!
    });
  },
  
  deleteDocument: (docId: number, token: string) =>
    apiRequest(`/documents/${docId}`, {
      method: "DELETE",
      token
    }),

  // --- Chat Sessions API ---
  listSessions: (token: string) =>
    apiRequest("/chat/sessions", {
      method: "GET",
      token
    }),
    
  createSession: (title: string | null, token: string) =>
    apiRequest("/chat/sessions", {
      method: "POST",
      token,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title })
    }),
    
  listMessages: (sessionId: number, token: string) =>
    apiRequest(`/chat/sessions/${sessionId}/messages`, {
      method: "GET",
      token
    }),
    
  deleteSession: (sessionId: number, token: string) =>
    apiRequest(`/chat/sessions/${sessionId}`, {
      method: "DELETE",
      token
    }),

  // --- Semantic Search API ---
  semanticSearch: (query: string, token: string) =>
    apiRequest(`/chat/search?q=${encodeURIComponent(query)}`, {
      method: "GET",
      token
    })
};

/**
 * Custom SSE Stream reader decoding server response tokens in real-time.
 */
export async function queryRAGStream(
  sessionId: number,
  content: string,
  token: string,
  callbacks: {
    onCitations: (citations: any[]) => void;
    onToken: (token: string) => void;
    onDone: () => void;
    onError: (error: string) => void;
  }
) {
  try {
    const response = await fetch(`${BASE_URL}/chat/sessions/${sessionId}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ content })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      let detail = "Failed to submit query.";
      try {
        detail = JSON.parse(errorText).detail || detail;
      } catch {
        detail = errorText || detail;
      }
      throw new Error(detail);
    }
    
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    if (!reader) {
      throw new Error("No readable response body stream found.");
    }
    
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      // Decode the raw byte array into text string
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      
      // Keep the last split item in buffer in case it arrived partially
      buffer = lines.pop() || "";
      
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith("data:")) continue;
        
        const dataContent = trimmed.substring(5).trim();
        if (dataContent === "[DONE]") {
          callbacks.onDone();
          continue;
        }
        
        try {
          const parsed = jsonParseSafe(dataContent);
          if (parsed.error) {
            callbacks.onError(parsed.error);
          } else if (parsed.citations) {
            callbacks.onCitations(parsed.citations);
          } else if (parsed.token !== undefined) {
            callbacks.onToken(parsed.token);
          }
        } catch (e) {
          console.error("Failed to parse event stream chunk", e);
        }
      }
    }
  } catch (err: any) {
    callbacks.onError(err.message || "An unexpected error occurred during streaming.");
  }
}

function jsonParseSafe(text: string): any {
  try {
    return JSON.parse(text);
  } catch {
    return {};
  }
}
