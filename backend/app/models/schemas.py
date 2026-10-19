"""Pydantic request/response schemas."""
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class DocumentStatus(str, Enum):
    uploading = "uploading"
    processing = "processing"
    embedding = "embedding"
    indexed = "indexed"
    ready = "ready"
    failed = "failed"


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str | None = None
    name: str
    size_bytes: int
    page_count: int
    chunk_count: int
    status: DocumentStatus
    error_message: str | None = None
    embedding_model: str | None = None
    created_at: datetime


class CitationOut(BaseModel):
    # populate_by_name lets us build it from ORM rows (document_name) or by field name (document).
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    document_id: str | None = None
    document: str = Field(validation_alias="document_name")
    page: int
    chunk_id: str
    text: str
    score: float
    retrieval_type: str


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    role: str
    content: str
    grounded: bool | None = None
    confidence: float | None = None
    metrics: dict | None = None
    created_at: datetime
    citations: list[CitationOut] = []


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str | None = None
    title: str
    created_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ConversationCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=255)


class ErrorResponse(BaseModel):
    detail: str


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    chunk_index: int
    page_number: int
    section: str | None = None
    text: str


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=20)
    mode: Literal["dense", "bm25", "hybrid"] = "hybrid"
    document_ids: list[str] | None = None


class SearchHit(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section: str | None = None
    text: str
    score: float
    retrieval_type: str = "hybrid"
    dense_score: float | None = None   # raw cosine similarity (hybrid mode)
    bm25_score: float | None = None    # raw BM25 score (hybrid mode)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None
    document_ids: list[str] | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)
    regenerate: bool = False  # replace the last question/answer pair instead of appending a new one


class ChatMetrics(BaseModel):
    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    evaluation_time_ms: float = 0.0   # time spent on the grounding check


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    grounded: bool | None = None      # None = no answer was generated / nothing to verify
    confidence: float | None = None   # 0..1 confidence that the answer is supported by the context
    faithfulness: float | None = None
    answer_relevance: float | None = None
    context_relevance: float | None = None
    unsupported_claims: list[str] = []  # sentences the context does not support (show a warning)
    citations: list[CitationOut] = []
    citation_coverage: float | None = None   # share of factual sentences with a valid citation
    invalid_citations: list[int] = []        # [Source N] numbers the model made up
    metrics: ChatMetrics


class RecentQuestion(BaseModel):
    id: str
    conversation_id: str
    question: str
    created_at: datetime


class EvaluationSummary(BaseModel):
    evaluated_answers: int = 0
    faithfulness: float | None = None
    answer_relevance: float | None = None
    context_relevance: float | None = None
    citation_coverage: float | None = None


class DashboardStats(BaseModel):
    total_documents: int
    total_pages: int
    total_chunks: int
    questions_asked: int
    avg_response_time_ms: float | None = None
    grounded_answers: int
    ungrounded_answers: int
    recent_documents: list[DocumentOut]
    recent_questions: list[RecentQuestion]
    evaluation: EvaluationSummary


class AppConfigOut(BaseModel):
    """Read-only, non-secret settings shown on the Settings page."""
    llm_provider: str
    llm_model: str
    embedding_model: str
    vector_store: str
    chunk_size: int
    chunk_overlap: int
    top_k: int
    dense_weight: float
    bm25_weight: float
    retrieval_threshold: float
    max_upload_mb: int
    block_ungrounded: bool


class EvaluateRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1, le=100)   # run only the first N questions
    top_k: int | None = Field(default=None, ge=1, le=20)


class EvaluationStatus(BaseModel):
    state: Literal["idle", "running", "completed", "failed"]
    completed: int = 0
    total: int = 0
    error: str | None = None
    started_at: str | None = None


class LiveMetrics(BaseModel):
    """Aggregates over real chat usage."""
    questions_asked: int
    evaluated_answers: int
    grounded_answers: int
    potentially_hallucinated_answers: int
    avg_retrieval_score: float | None = None
    avg_response_time_ms: float | None = None
    faithfulness: float | None = None
    answer_relevance: float | None = None
    context_relevance: float | None = None
    citation_coverage: float | None = None


class SampleRunOut(BaseModel):
    label: str
    note: str
    generated_at: str
    config: dict
    summary: dict


class EvaluationMetricsOut(BaseModel):
    live: LiveMetrics
    sample: SampleRunOut | None = None


class EvaluationResultsOut(BaseModel):
    label: str
    generated_at: str
    results: list[dict]


class VectorBenchmarkOut(BaseModel):
    label: str
    note: str
    generated_at: str
    environment: dict
    parameters: dict
    stores: dict
    real_documents: dict | None = None
