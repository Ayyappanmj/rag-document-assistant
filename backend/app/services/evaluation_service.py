"""Runs the evaluation dataset through the real RAG pipeline and stores the results."""
import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.models.database import Citation, Document, Evaluation, Message
from app.models.schemas import LiveMetrics
from app.rag.eval_metrics import answer_match, retrieval_precision_recall, summarize
from app.services.chat_service import ChatService
from app.services.document_service import process_document

logger = logging.getLogger(__name__)

LABEL = "Sample Evaluation"
NOTE = (
    "Heuristic scores on a small synthetic dataset about fictional documents. "
    "This is a sanity check for the pipeline, not a scientific benchmark."
)


class EvaluationSetupError(Exception):
    """User-fixable problem (missing dataset, missing documents)."""


# ------------------------------------------------------------------ files
def load_questions(evaluation_dir: str) -> list[dict]:
    path = Path(evaluation_dir) / "questions.json"
    if not path.exists():
        raise EvaluationSetupError(f"Dataset not found: {path}")
    try:
        questions = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvaluationSetupError("questions.json is not valid JSON.") from exc
    if not isinstance(questions, list) or not questions:
        raise EvaluationSetupError("questions.json must contain a non-empty list of questions.")
    return questions


def save_results(evaluation_dir: str, run: dict) -> None:
    path = Path(evaluation_dir) / "results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(run, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)  # never leaves a half-written file


def load_results(evaluation_dir: str) -> dict | None:
    path = Path(evaluation_dir) / "results.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) and "summary" in data else None  # the shipped file is just []


# ------------------------------------------------------------------ documents
def expected_document_names(questions: list[dict]) -> set[str]:
    return {name for q in questions for name in q.get("expected_sources", [])}


def resolve_document_ids(db: Session, names: set[str]) -> tuple[list[str], list[str]]:
    """Returns (ids of ready documents with these names, names that have no ready document)."""
    rows = db.execute(select(Document.id, Document.name).where(Document.status == "ready")).all()
    ids = [doc_id for doc_id, name in rows if name in names]
    present = {name for _, name in rows}
    return ids, sorted(names - present)


def ingest_sample_documents(session_factory: sessionmaker, settings: Settings) -> list[str]:
    """CLI helper: process evaluation/sample_docs/*.pdf (skipping ones already uploaded). Returns names added."""
    sample_dir = Path(settings.evaluation_dir) / "sample_docs"
    added: list[str] = []
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    for pdf in sorted(sample_dir.glob("*.pdf")):
        with session_factory() as db:
            exists = db.scalar(
                select(Document.id).where(Document.name == pdf.name, Document.status == "ready")
            )
            if exists:
                continue
            stored = f"{uuid.uuid4().hex}.pdf"
            shutil.copy(pdf, upload_dir / stored)
            doc = Document(
                name=pdf.name, stored_filename=stored, size_bytes=pdf.stat().st_size,
                status="processing", embedding_model=settings.embedding_model,
            )
            db.add(doc)
            db.commit()
            doc_id = doc.id
        process_document(doc_id, session_factory)  # synchronous here
        added.append(pdf.name)
    return added


# ------------------------------------------------------------------ the run
def _evaluate_question(
    pipeline: ChatService, q: dict, document_ids: list[str], top_k: int | None,
) -> dict:
    r = pipeline.run_pipeline(q["question"], document_ids, top_k)
    expected = q.get("expected_sources", [])
    answerable = bool(q.get("answerable", bool(expected)))
    precision, recall = retrieval_precision_recall([c.document_name for c in r.retrieved], expected)
    dense = [c.dense_score for c in r.retrieved if c.dense_score is not None]
    g = r.grounding
    return {
        "id": q.get("id"),
        "type": q.get("type", "factual"),
        "question": q["question"],
        "expected_answer": q.get("ground_truth", ""),
        "expected_sources": expected,
        "answerable": answerable,
        "retrieved_context": [
            {"document": c.document_name, "page": c.page_number, "score": round(c.dense_score or c.score, 3),
             "text": c.text}
            for c in r.retrieved
        ],
        "generated_answer": r.answer,
        "refused": r.refused,
        "grounded": g.grounded if g else None,
        "confidence": g.confidence if g and g.grounded is not None else None,
        "faithfulness": g.faithfulness if g and g.grounded is not None else None,
        "answer_relevance": r.answer_relevance,
        "context_relevance": r.context_relevance,
        "citation_coverage": r.coverage,
        "retrieval_precision": precision,
        "retrieval_recall": recall,
        "top_retrieval_score": round(max(dense), 3) if dense else None,
        "answer_match": answer_match(q.get("ground_truth", ""), r.answer) if answerable else None,
        "latency_ms": r.metrics.total_time_ms,
    }


def run_evaluation(
    db: Session, pipeline: ChatService, settings: Settings, questions: list[dict],
    document_ids: list[str], top_k: int | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> dict:
    """Runs every question, stores `is_sample` Evaluation rows, writes results.json and returns the run."""
    db.execute(delete(Evaluation).where(Evaluation.is_sample.is_(True)))  # keep only the latest run
    db.commit()

    rows: list[dict] = []
    for i, q in enumerate(questions, start=1):
        row = _evaluate_question(pipeline, q, document_ids, top_k)
        rows.append(row)
        if row["faithfulness"] is not None or row["answer_relevance"] is not None:
            db.add(Evaluation(
                question=row["question"], faithfulness=row["faithfulness"],
                answer_relevance=row["answer_relevance"], context_relevance=row["context_relevance"],
                citation_coverage=row["citation_coverage"], latency_ms=row["latency_ms"], is_sample=True,
            ))
            db.commit()
        if progress:
            progress(i, len(questions))

    llm_model = settings.ollama_model if settings.llm_provider.lower() == "ollama" else settings.openai_model
    run = {
        "label": LABEL,
        "note": NOTE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "llm_provider": settings.llm_provider, "llm_model": llm_model,
            "embedding_model": settings.embedding_model, "top_k": top_k or settings.top_k,
            "dense_weight": settings.dense_weight, "bm25_weight": settings.bm25_weight,
            "retrieval_threshold": settings.retrieval_threshold,
            "chunk_size": settings.chunk_size, "chunk_overlap": settings.chunk_overlap,
        },
        "summary": summarize(rows),
        "results": rows,
    }
    save_results(settings.evaluation_dir, run)
    logger.info("evaluation_finished questions=%d", len(rows))
    return run


# ------------------------------------------------------------------ live metrics
def get_live_metrics(db: Session) -> LiveMetrics:
    questions = db.scalar(select(func.count(Message.id)).where(Message.role == "user")) or 0
    grounded = db.scalar(select(func.count(Message.id)).where(Message.grounded.is_(True))) or 0
    ungrounded = db.scalar(select(func.count(Message.id)).where(Message.grounded.is_(False))) or 0
    f, ar, cr, cc, lat, n = db.execute(
        select(
            func.avg(Evaluation.faithfulness), func.avg(Evaluation.answer_relevance),
            func.avg(Evaluation.context_relevance), func.avg(Evaluation.citation_coverage),
            func.avg(Evaluation.latency_ms), func.count(Evaluation.id),
        ).where(Evaluation.is_sample.is_(False))
    ).one()
    avg_score = db.scalar(select(func.avg(Citation.score)))

    def r3(v: float | None) -> float | None:
        return round(float(v), 3) if v is not None else None

    return LiveMetrics(
        questions_asked=questions, evaluated_answers=n, grounded_answers=grounded,
        potentially_hallucinated_answers=ungrounded, avg_retrieval_score=r3(avg_score),
        avg_response_time_ms=round(float(lat), 1) if lat is not None else None,
        faithfulness=r3(f), answer_relevance=r3(ar), context_relevance=r3(cr), citation_coverage=r3(cc),
    )
