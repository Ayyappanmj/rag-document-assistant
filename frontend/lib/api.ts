import type {
  AppConfig, AuthResponse, ChatRequestBody, ChatResponse, ChunkRecord, Citation,
  ConversationDetail, ConversationSummary, DashboardStats, DocumentRecord,
  EvaluationMetrics, EvaluationResults, EvaluationStatus, HealthStatus, UserRecord, VectorBenchmark,
} from "@/types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

const unreachable = () =>
  new ApiError(`Cannot reach the backend at ${API_URL}. Is it running?`, 0);

let memoryToken: string | null = null;

export function getAuthToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("rag_token") || memoryToken;
  }
  return memoryToken;
}

export function setAuthToken(token: string | null) {
  memoryToken = token;
  if (typeof window !== "undefined") {
    if (token) localStorage.setItem("rag_token", token);
    else localStorage.removeItem("rag_token");
  }
}

function extractDetail(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : "")).join(", ");
    }
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  const token = getAuthToken();
  const headers = new Headers(init?.headers);
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  try {
    res = await fetch(`${API_URL}${path}`, { cache: "no-store", ...init, headers });
  } catch {
    throw unreachable();
  }
  if (!res.ok) {
    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      /* response had no JSON body */
    }
    throw new ApiError(extractDetail(body, res.statusText || "Request failed"), res.status);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// ---------- auth ----------
export const registerUser = (body: { email: string; password: string }) =>
  request<AuthResponse>("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const loginUser = (body: { email: string; password: string }) =>
  request<AuthResponse>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const getMe = () => request<UserRecord>("/api/auth/me");

// ---------- core system ----------
export const getHealth = () => request<HealthStatus>("/api/health");
export const getConfig = () => request<AppConfig>("/api/config");
export const getDashboardStats = () => request<DashboardStats>("/api/dashboard/stats");
export const listDocuments = () => request<DocumentRecord[]>("/api/documents");
export const deleteDocument = (id: string) => request<void>(`/api/documents/${id}`, { method: "DELETE" });
export const getChunks = (id: string, page?: number, limit = 50) => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (page) params.set("page", String(page));
  return request<ChunkRecord[]>(`/api/documents/${id}/chunks?${params}`);
};

/** Upload with progress (fetch cannot report upload progress, so XMLHttpRequest is used). */
export function uploadDocument(file: File, onProgress?: (percent: number) => void): Promise<DocumentRecord> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/api/documents/upload`);
    const token = getAuthToken();
    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.(Math.round((e.loaded / e.total) * 100));
    };
    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        /* not JSON */
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as DocumentRecord);
      else reject(new ApiError(extractDetail(body, "Upload failed"), xhr.status));
    };
    xhr.onerror = () => reject(unreachable());
    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

// ---------- chat ----------
export const sendChat = (body: ChatRequestBody) =>
  request<ChatResponse>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export async function sendChatStream(
  body: ChatRequestBody,
  onToken: (token: string) => void,
  onSources?: (sources: Citation[]) => void,
): Promise<ChatResponse> {
  const token = getAuthToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/chat/stream`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
  } catch {
    throw unreachable();
  }

  if (!res.ok) {
    let errBody: unknown = null;
    try {
      errBody = await res.json();
    } catch {
      /* ignore */
    }
    throw new ApiError(extractDetail(errBody, "Streaming request failed"), res.status);
  }

  const reader = res.body?.getReader();
  if (!reader) {
    throw new ApiError("Streaming response body is not readable", 500);
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let finalResponse: ChatResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() ?? "";

    for (const chunk of lines) {
      const trimmed = chunk.trim();
      if (!trimmed.startsWith("data: ")) continue;
      try {
        const data = JSON.parse(trimmed.slice(6));
        if (data.type === "token") {
          onToken(data.token);
        } else if (data.type === "sources" && onSources) {
          onSources(data.sources);
        } else if (data.type === "done") {
          finalResponse = data.response as ChatResponse;
        } else if (data.type === "error") {
          throw new ApiError(data.error || "Generation error", 500);
        }
      } catch (e) {
        if (e instanceof ApiError) throw e;
      }
    }
  }

  if (!finalResponse) {
    throw new ApiError("Stream ended without completion response", 500);
  }
  return finalResponse;
}

export const listConversations = () => request<ConversationSummary[]>("/api/conversations");
export const getConversation = (id: string) => request<ConversationDetail>(`/api/conversations/${id}`);
export const deleteConversation = (id: string) =>
  request<void>(`/api/conversations/${id}`, { method: "DELETE" });

// ---------- evaluation ----------
export const getEvaluationMetrics = () => request<EvaluationMetrics>("/api/evaluation/metrics");
export const getEvaluationStatus = () => request<EvaluationStatus>("/api/evaluation/status");
export const getEvaluationResults = () => request<EvaluationResults>("/api/evaluation/results");
export const startEvaluation = (body: { limit?: number; top_k?: number } = {}) =>
  request<void>("/api/evaluation/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
export const getVectorBenchmark = () => request<VectorBenchmark>("/api/evaluation/benchmark");
export const getVectorStoreComparison = () => request<VectorBenchmark>("/api/evaluation/vector-stores");
