"""Search endpoint: dense (FAISS), bm25, or hybrid (default)."""
import logging
import time
from dataclasses import asdict

from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import SearchHit, SearchRequest
from app.rag import dependencies as deps

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=list[SearchHit])
def search(body: SearchRequest):
    top_k = body.top_k or get_settings().top_k
    started = time.perf_counter()
    if body.mode == "hybrid":
        results = deps.get_hybrid_retriever().retrieve(body.query, top_k, body.document_ids)
    elif body.mode == "bm25":
        results = deps.get_bm25_retriever().search(body.query, top_k, body.document_ids)
    else:
        store = deps.get_vector_store()
        if store.count == 0:
            return []
        query_vec = deps.get_embedding_service().embed_query(body.query)
        results = store.search(query_vec, top_k, body.document_ids)
    logger.info("%s_search results=%d latency_ms=%.1f", body.mode, len(results), (time.perf_counter() - started) * 1000)
    return [SearchHit(**{**asdict(r), "retrieval_type": body.mode}) for r in results]
