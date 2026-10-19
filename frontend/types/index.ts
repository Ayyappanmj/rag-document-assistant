export type DocumentStatus = "uploading" | "processing" | "embedding" | "indexed" | "ready" | "failed";

export interface UserRecord {
  id: string;
  email: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserRecord;
}

export interface DocumentRecord {
  id: string;
  user_id?: string | null;
  name: string;
  size_bytes: number;
  page_count: number;
  chunk_count: number;
  status: DocumentStatus;
  error_message: string | null;
  embedding_model: string | null;
  created_at: string;
}

export interface ChunkRecord {
  id: string;
  chunk_index: number;
  page_number: number;
  section: string | null;
  text: string;
}

export interface RecentQuestion {
  id: string;
  conversation_id: string;
  question: string;
  created_at: string;
}

export interface EvaluationSummary {
  evaluated_answers: number;
  faithfulness: number | null;
  answer_relevance: number | null;
  context_relevance: number | null;
  citation_coverage: number | null;
}

export interface DashboardStats {
  total_documents: number;
  total_pages: number;
  total_chunks: number;
  questions_asked: number;
  avg_response_time_ms: number | null;
  grounded_answers: number;
  ungrounded_answers: number;
  recent_documents: DocumentRecord[];
  recent_questions: RecentQuestion[];
  evaluation: EvaluationSummary;
}

export interface AppConfig {
  llm_provider: string;
  llm_model: string;
  embedding_model: string;
  vector_store: string;
  chunk_size: number;
  chunk_overlap: number;
  top_k: number;
  dense_weight: number;
  bm25_weight: number;
  retrieval_threshold: number;
  max_upload_mb: number;
  block_ungrounded: boolean;
}

export interface HealthStatus {
  status: string;
  app: string;
  environment: string;
  llm_provider: string;
}

// ---------- chat ----------
export interface Citation {
  document_id?: string | null;
  document: string;
  page: number;
  chunk_id: string;
  text: string;
  score: number;
  retrieval_type: string;
}

export interface ChatMetrics {
  retrieval_time_ms: number;
  generation_time_ms: number;
  total_time_ms: number;
  evaluation_time_ms: number;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  answer: string;
  grounded: boolean | null;
  confidence: number | null;
  faithfulness: number | null;
  answer_relevance: number | null;
  context_relevance: number | null;
  unsupported_claims: string[];
  citations: Citation[];
  citation_coverage: number | null;
  invalid_citations: number[];
  metrics: ChatMetrics;
}

export interface ChatRequestBody {
  question: string;
  conversation_id: string | null;
  document_ids: string[] | null;
  regenerate: boolean;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
}

export interface MessageRecord {
  id: string;
  role: "user" | "assistant";
  content: string;
  grounded: boolean | null;
  confidence: number | null;
  metrics: Record<string, unknown> | null;
  created_at: string;
  citations: Citation[];
}

export interface ConversationDetail extends ConversationSummary {
  messages: MessageRecord[];
}

/** One message as the chat UI shows it (built from either a live response or a saved record). */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  grounded: boolean | null;
  confidence: number | null;
  unsupportedClaims: string[];
  citationCoverage: number | null;
  invalidCitations: number[];
  totalMs: number | null;
  retrievalMs: number | null;
  generationMs: number | null;
  error?: string;
  question?: string; // set on error bubbles so the question can be retried
  streaming?: boolean;
}

// ---------- evaluation ----------
export interface EvaluationStatus {
  state: "idle" | "running" | "completed" | "failed";
  completed: number;
  total: number;
  error: string | null;
  started_at: string | null;
}

export interface LiveMetrics {
  questions_asked: number;
  evaluated_answers: number;
  grounded_answers: number;
  potentially_hallucinated_answers: number;
  avg_retrieval_score: number | null;
  avg_response_time_ms: number | null;
  faithfulness: number | null;
  answer_relevance: number | null;
  context_relevance: number | null;
  citation_coverage: number | null;
}

export interface TypeSummary {
  count: number;
  answer_match: number | null;
  faithfulness: number | null;
  avg_latency_ms: number | null;
}

export interface SampleSummary {
  total_questions: number;
  answerable_questions: number;
  unanswerable_questions: number;
  faithfulness: number | null;
  answer_relevance: number | null;
  context_relevance: number | null;
  citation_coverage: number | null;
  retrieval_precision: number | null;
  retrieval_recall: number | null;
  avg_retrieval_score: number | null;
  answer_match: number | null;
  avg_latency_ms: number | null;
  grounded_answers: number;
  potentially_hallucinated_answers: number;
  refusal_accuracy: number | null;
  false_refusal_rate: number | null;
  by_type: Record<string, TypeSummary>;
}

export interface SampleRun {
  label: string;
  note: string;
  generated_at: string;
  config: Record<string, string | number>;
  summary: SampleSummary;
}

export interface EvaluationMetrics {
  live: LiveMetrics;
  sample: SampleRun | null;
}

export interface RetrievedChunk {
  document: string;
  page: number;
  score: number;
  text: string;
}

export interface EvaluationRow {
  id: string | null;
  type: string;
  question: string;
  expected_answer: string;
  expected_sources: string[];
  answerable: boolean;
  retrieved_context: RetrievedChunk[];
  generated_answer: string;
  refused: boolean;
  grounded: boolean | null;
  confidence: number | null;
  faithfulness: number | null;
  answer_relevance: number | null;
  context_relevance: number | null;
  citation_coverage: number | null;
  retrieval_precision: number | null;
  retrieval_recall: number | null;
  top_retrieval_score: number | null;
  answer_match: number | null;
  latency_ms: number;
}

export interface EvaluationResults {
  label: string;
  generated_at: string;
  results: EvaluationRow[];
}

// ---------- vector store comparison ----------
export interface LatencyStats {
  mean: number;
  p50: number;
  p95: number;
}

export interface StoreBenchmark {
  index_type: string;
  build_seconds: number;
  vectors_per_second: number | null;
  disk_mb: number;
  open_seconds: number;
  reopened_vectors: number;
  query_ms: LatencyStats;
  filtered_query_ms: LatencyStats;
  recall_at_k: number;
  filtered_recall_at_k: number;
  filter_correct: boolean;
  delete_document_ms: number;
  deleted_vectors: number;
}

export interface StoreBenchmarkError {
  error: string;
}

export interface RealDocumentsComparison {
  questions: number;
  top_k: number;
  stores: Record<
    string,
    { retrieval_precision: number | null; retrieval_recall: number | null; avg_query_ms: number | null; vectors: number }
  >;
  top_k_overlap_jaccard: number | null;
}

export interface VectorBenchmark {
  label: string;
  note: string;
  generated_at: string;
  environment: Record<string, string | number | null>;
  parameters: Record<string, string | number>;
  stores: Record<string, StoreBenchmark | StoreBenchmarkError>;
  real_documents: RealDocumentsComparison | null;
}
