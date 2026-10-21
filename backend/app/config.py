"""Central application settings, loaded from environment variables / .env."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "RAG Document Assistant"
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"  # comma-separated list

    database_url: str = "sqlite:///./rag.db"

    llm_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    # Optional OpenAI-compatible provider (OpenAI, Groq, LM Studio, vLLM...). Set LLM_PROVIDER=openai to use.
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""  # backend-only; never sent to the frontend
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    llm_timeout_seconds: float = 120.0
    llm_temperature: float = 0.1

    embedding_provider: str = "local"  # "local" | "openai" | "ollama" | "gemini" | "fastembed"
    embedding_api_key: str = ""        # optional override; defaults to openai_api_key or gemini_api_key
    embedding_base_url: str = ""       # optional override; defaults to openai_base_url or ollama_base_url
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chunk_size: int = 800
    chunk_overlap: int = 150
    embedding_batch_size: int = 8
    vector_store: str = "faiss"  # "faiss" or "chroma" (needs requirements-chroma.txt)
    candidate_pool: int = 20
    max_context_chars: int = 6000
    top_k: int = 5
    dense_weight: float = 0.7
    bm25_weight: float = 0.3
    retrieval_threshold: float = 0.35
    grounding_support_threshold: float = 0.5   # per-sentence support needed to count as supported
    grounding_min_faithfulness: float = 0.8    # share of supported sentences needed for grounded=True
    block_ungrounded: bool = False             # if True, replace ungrounded answers with 'insufficient evidence'

    max_upload_mb: int = 25
    upload_dir: str = str(BACKEND_DIR / "data" / "uploads")
    index_dir: str = str(BACKEND_DIR / "data" / "indexes")
    chroma_dir: str = str(BACKEND_DIR / "data" / "chroma")
    evaluation_dir: str = str(BACKEND_DIR.parent / "evaluation")  # questions.json, results.json, sample_docs/
    secret_key: str = "change-this-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Re-ranking configuration
    reranker_enabled: bool = False
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # OCR configuration
    ocr_enabled: bool = True
    ocr_language: str = "eng"
    ocr_min_char_count: int = 30
    ocr_tesseract_cmd: str | None = None  # optional custom tesseract path

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
