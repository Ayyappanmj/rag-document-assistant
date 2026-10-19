"""Dashboard statistics and read-only configuration."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import get_optional_current_user
from app.models.database import User, get_db
from app.models.schemas import AppConfigOut, DashboardStats
from app.services.dashboard_service import get_dashboard_stats

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard/stats", response_model=DashboardStats)
def dashboard_stats(
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    user_id = current_user.id if current_user else None
    return get_dashboard_stats(db, user_id=user_id)


@router.get("/config", response_model=AppConfigOut)
def app_config():
    s = get_settings()
    return AppConfigOut(  # explicit fields only, so secrets can never leak
        llm_provider=s.llm_provider,
        llm_model=s.ollama_model if s.llm_provider.lower() == "ollama" else s.openai_model,
        embedding_model=s.embedding_model, vector_store=s.vector_store.lower(), chunk_size=s.chunk_size, chunk_overlap=s.chunk_overlap,
        top_k=s.top_k, dense_weight=s.dense_weight, bm25_weight=s.bm25_weight,
        retrieval_threshold=s.retrieval_threshold, max_upload_mb=s.max_upload_mb,
        block_ungrounded=s.block_ungrounded,
    )
