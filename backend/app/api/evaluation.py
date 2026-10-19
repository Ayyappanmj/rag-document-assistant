"""Evaluation endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models.database import get_db, get_session_factory
from app.models.schemas import (
    EvaluateRequest, EvaluationMetricsOut, EvaluationResultsOut, EvaluationStatus, SampleRunOut,
    VectorBenchmarkOut,
)
from app.rag import dependencies as deps
from app.services.chat_service import ChatService
from app.services.evaluation_jobs import job_manager
from app.services.evaluation_service import (
    EvaluationSetupError, expected_document_names, get_live_metrics, load_questions, load_results,
    resolve_document_ids, run_evaluation,
)

import json
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["evaluation"])


@router.post("/evaluate", response_model=EvaluationStatus, status_code=status.HTTP_202_ACCEPTED)
def start_evaluation(
    body: EvaluateRequest | None = None,
    db: Session = Depends(get_db),
    session_factory: sessionmaker = Depends(get_session_factory),
):
    """Starts the sample evaluation in the background. Poll GET /api/evaluation/status."""
    settings = get_settings()
    body = body or EvaluateRequest()
    try:
        all_questions = load_questions(settings.evaluation_dir)
    except EvaluationSetupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))

    document_ids, missing = resolve_document_ids(db, expected_document_names(all_questions))
    if missing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Upload these sample documents first (create them with python evaluation/make_sample_pdfs.py): "
            + ", ".join(missing),
        )
    questions = all_questions[: body.limit] if body.limit else all_questions

    def runner(progress):
        with session_factory() as run_db:
            pipeline = ChatService(
                run_db, deps.get_hybrid_retriever(), deps.get_generator(), deps.get_grounding_evaluator(), settings
            )
            run_evaluation(run_db, pipeline, settings, questions, document_ids, body.top_k, progress)

    if not job_manager.start(runner, total=len(questions)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An evaluation is already running.")
    return EvaluationStatus(**job_manager.status())


@router.get("/evaluation/status", response_model=EvaluationStatus)
def evaluation_status():
    return EvaluationStatus(**job_manager.status())


@router.get("/evaluation/metrics", response_model=EvaluationMetricsOut)
def evaluation_metrics(db: Session = Depends(get_db)):
    run = load_results(get_settings().evaluation_dir)
    return EvaluationMetricsOut(
        live=get_live_metrics(db),
        sample=SampleRunOut(**{k: run[k] for k in ("label", "note", "generated_at", "config", "summary")})
        if run else None,
    )


@router.get("/evaluation/results", response_model=EvaluationResultsOut)
def evaluation_results():
    run = load_results(get_settings().evaluation_dir)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No sample evaluation has been run yet.")
    return EvaluationResultsOut(label=run["label"], generated_at=run["generated_at"], results=run["results"])


@router.get("/evaluation/vector-stores", response_model=VectorBenchmarkOut)
def vector_store_comparison():
    """Last FAISS vs Chroma benchmark (created by: python evaluation/compare_vector_stores.py)."""
    path = Path(get_settings().evaluation_dir) / "vector_store_comparison.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = None
    if not isinstance(data, dict) or "stores" not in data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No vector store comparison has been run yet.")
    return VectorBenchmarkOut(**data)
