"""Chat endpoints: standard and streaming."""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import get_optional_current_user
from app.models.database import Document, User, get_db
from app.models.schemas import ChatRequest, ChatResponse
from app.rag import dependencies as deps
from app.rag.generator import LLMError
from app.services.chat_service import ChatService, ConversationNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


def _resolve_user_documents(
    requested_ids: list[str] | None,
    current_user: User | None,
    db: Session,
) -> list[str] | None:
    if current_user:
        user_docs = set(
            db.scalars(
                select(Document.id).where(
                    (Document.user_id == current_user.id) | (Document.user_id.is_(None))
                )
            ).all()
        )
    else:
        user_docs = set(
            db.scalars(select(Document.id).where(Document.user_id.is_(None))).all()
        )
    if requested_ids is not None:
        valid_ids = [doc_id for doc_id in requested_ids if doc_id in user_docs]
        return valid_ids if valid_ids else ["__none__"]
    return list(user_docs) if user_docs else ["__none__"]


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    doc_ids = _resolve_user_documents(body.document_ids, current_user, db)
    service = ChatService(
        db, deps.get_hybrid_retriever(), deps.get_generator(), deps.get_grounding_evaluator(), get_settings()
    )
    user_id = current_user.id if current_user else None
    try:
        return service.answer(
            body.question, body.conversation_id, doc_ids, body.top_k, body.regenerate, user_id=user_id
        )
    except ConversationNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    except LLMError as exc:
        logger.error("llm_failed reason=%s", exc)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))


@router.post("/stream")
def chat_stream(
    body: ChatRequest,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    doc_ids = _resolve_user_documents(body.document_ids, current_user, db)
    service = ChatService(
        db, deps.get_hybrid_retriever(), deps.get_generator(), deps.get_grounding_evaluator(), get_settings()
    )
    user_id = current_user.id if current_user else None
    try:
        stream_gen = service.stream_answer(
            body.question, body.conversation_id, doc_ids, body.top_k, body.regenerate, user_id=user_id
        )
        return StreamingResponse(stream_gen, media_type="text/event-stream")
    except ConversationNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
