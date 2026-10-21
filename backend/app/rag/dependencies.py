"""Shared singletons (model + index are expensive, so create them once)."""
from functools import lru_cache

from app.config import get_settings
from app.models.database import SessionLocal
from app.rag.bm25_retriever import BM25Retriever
from app.rag.embeddings import EmbeddingService
from app.rag.evaluator import GroundingEvaluator
from app.rag.generator import Generator, create_llm_client
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.reranker import ReRanker
from app.rag.vector_factory import create_vector_store
from app.rag.vector_types import VectorIndex


@lru_cache
def get_embedding_service() -> EmbeddingService:
    s = get_settings()
    api_key = s.embedding_api_key or (s.gemini_api_key if s.embedding_provider in ("gemini", "google") else s.openai_api_key)
    base_url = s.embedding_base_url or (s.openai_base_url if s.embedding_provider == "openai" else s.ollama_base_url)
    return EmbeddingService(
        model_name=s.embedding_model,
        batch_size=s.embedding_batch_size,
        provider=s.embedding_provider,
        api_key=api_key,
        base_url=base_url,
    )


@lru_cache
def get_vector_store() -> VectorIndex:
    return create_vector_store(get_settings())


@lru_cache
def get_bm25_retriever() -> BM25Retriever:
    return BM25Retriever(SessionLocal)


@lru_cache
def get_reranker() -> ReRanker:
    s = get_settings()
    return ReRanker(model_name=s.reranker_model, enabled=s.reranker_enabled)


def get_hybrid_retriever() -> HybridRetriever:
    """Cheap to build (just holds references), so deliberately not cached."""
    s = get_settings()
    reranker = get_reranker() if s.reranker_enabled else None
    return HybridRetriever(
        get_embedding_service(), get_vector_store(), get_bm25_retriever(),
        s.dense_weight, s.bm25_weight, s.candidate_pool, reranker=reranker,
    )


def get_generator() -> Generator:
    """Not cached, so changing settings or patching in tests takes effect immediately."""
    return Generator(create_llm_client(get_settings()))


def get_grounding_evaluator() -> GroundingEvaluator:
    s = get_settings()
    return GroundingEvaluator(get_embedding_service(), s.grounding_support_threshold, s.grounding_min_faithfulness)
