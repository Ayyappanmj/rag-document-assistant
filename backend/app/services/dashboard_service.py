"""Aggregates numbers for the dashboard."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.database import Document, Evaluation, Message
from app.models.schemas import DashboardStats, EvaluationSummary, RecentQuestion

RECENT_LIMIT = 5
LATENCY_SAMPLE = 500  # average over the latest N answers, enough for a dashboard


def _round(value: float | None) -> float | None:
    return round(float(value), 3) if value is not None else None


def get_dashboard_stats(db: Session, user_id: str | None = None) -> DashboardStats:
    doc_query = select(
        func.count(Document.id),
        func.coalesce(func.sum(Document.page_count), 0),
        func.coalesce(func.sum(Document.chunk_count), 0),
    )
    if user_id:
        doc_query = doc_query.where(Document.user_id == user_id)
    total_docs, total_pages, total_chunks = db.execute(doc_query).one()

    msg_base = select(func.count(Message.id)).where(Message.role == "user")
    grounded_base = select(func.count(Message.id)).where(Message.grounded.is_(True))
    ungrounded_base = select(func.count(Message.id)).where(Message.grounded.is_(False))

    if user_id:
        from app.models.database import Conversation
        user_convs = select(Conversation.id).where(Conversation.user_id == user_id)
        msg_base = msg_base.where(Message.conversation_id.in_(user_convs))
        grounded_base = grounded_base.where(Message.conversation_id.in_(user_convs))
        ungrounded_base = ungrounded_base.where(Message.conversation_id.in_(user_convs))

    questions = db.scalar(msg_base) or 0
    grounded = db.scalar(grounded_base) or 0
    ungrounded = db.scalar(ungrounded_base) or 0

    metric_query = (
        select(Message.metrics)
        .where(Message.role == "assistant", Message.metrics.is_not(None))
        .order_by(Message.created_at.desc())
        .limit(LATENCY_SAMPLE)
    )
    if user_id:
        metric_query = metric_query.where(Message.conversation_id.in_(user_convs))
    metric_rows = db.scalars(metric_query).all()
    times = [m["total_time_ms"] for m in metric_rows if isinstance(m, dict) and m.get("total_time_ms") is not None]
    avg_ms = round(sum(times) / len(times), 1) if times else None

    recent_docs_q = select(Document).order_by(Document.created_at.desc()).limit(RECENT_LIMIT)
    if user_id:
        recent_docs_q = select(Document).where(Document.user_id == user_id).order_by(Document.created_at.desc()).limit(RECENT_LIMIT)
    recent_docs = db.scalars(recent_docs_q).all()

    recent_q_query = select(Message).where(Message.role == "user").order_by(Message.created_at.desc()).limit(RECENT_LIMIT)
    if user_id:
        recent_q_query = recent_q_query.where(Message.conversation_id.in_(user_convs))
    recent_questions = db.scalars(recent_q_query).all()

    f, ar, cr, cc, n = db.execute(
        select(
            func.avg(Evaluation.faithfulness), func.avg(Evaluation.answer_relevance),
            func.avg(Evaluation.context_relevance), func.avg(Evaluation.citation_coverage),
            func.count(Evaluation.id),
        ).where(Evaluation.is_sample.is_(False))
    ).one()

    return DashboardStats(
        total_documents=total_docs,
        total_pages=int(total_pages),
        total_chunks=int(total_chunks),
        questions_asked=questions,
        avg_response_time_ms=avg_ms,
        grounded_answers=grounded,
        ungrounded_answers=ungrounded,
        recent_documents=recent_docs,
        recent_questions=[
            RecentQuestion(id=m.id, conversation_id=m.conversation_id, question=m.content, created_at=m.created_at)
            for m in recent_questions
        ],
        evaluation=EvaluationSummary(
            evaluated_answers=n, faithfulness=_round(f), answer_relevance=_round(ar),
            context_relevance=_round(cr), citation_coverage=_round(cc),
        ),
    )
