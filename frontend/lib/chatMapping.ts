import type { ChatMessage, ChatResponse, MessageRecord } from "@/types";

export function uid(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

const num = (v: unknown): number | null => (typeof v === "number" ? v : null);
const numList = (v: unknown): number[] => (Array.isArray(v) ? v.filter((x): x is number => typeof x === "number") : []);
const strList = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : []);

const base = (): Omit<ChatMessage, "id" | "role" | "content"> => ({
  citations: [],
  grounded: null,
  confidence: null,
  unsupportedClaims: [],
  citationCoverage: null,
  invalidCitations: [],
  totalMs: null,
  retrievalMs: null,
  generationMs: null,
});

export function userMessage(content: string): ChatMessage {
  return { id: uid(), role: "user", content, ...base() };
}

export function errorMessage(error: string, question: string): ChatMessage {
  return { id: uid(), role: "assistant", content: "", error, question, ...base() };
}

export function fromResponse(r: ChatResponse): ChatMessage {
  return {
    id: r.message_id,
    role: "assistant",
    content: r.answer,
    citations: r.citations,
    grounded: r.grounded,
    confidence: r.confidence,
    unsupportedClaims: r.unsupported_claims,
    citationCoverage: r.citation_coverage,
    invalidCitations: r.invalid_citations,
    totalMs: r.metrics.total_time_ms,
    retrievalMs: r.metrics.retrieval_time_ms,
    generationMs: r.metrics.generation_time_ms,
  };
}

/** Saved messages keep their scores inside the `metrics` JSON, so unpack them here. */
export function fromRecord(m: MessageRecord): ChatMessage {
  const metrics = m.metrics ?? {};
  return {
    id: m.id,
    role: m.role,
    content: m.content,
    citations: m.citations,
    grounded: m.grounded,
    confidence: m.confidence,
    unsupportedClaims: strList(metrics.unsupported_claims),
    citationCoverage: num(metrics.citation_coverage),
    invalidCitations: numList(metrics.invalid_citations),
    totalMs: num(metrics.total_time_ms),
    retrievalMs: num(metrics.retrieval_time_ms),
    generationMs: num(metrics.generation_time_ms),
  };
}
