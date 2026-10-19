"""Conversation endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_optional_current_user
from app.models.database import Conversation, User, get_db
from app.models.schemas import ConversationCreate, ConversationDetail, ConversationOut

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: ConversationCreate,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    conv = Conversation(
        title=body.title,
        user_id=current_user.id if current_user else None,
    )
    db.add(conv)
    db.commit()
    return conv


@router.get("", response_model=list[ConversationOut])
def list_conversations(
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    query = select(Conversation)
    if current_user:
        query = query.where(Conversation.user_id == current_user.id)
    return db.scalars(query.order_by(Conversation.created_at.desc())).all()


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: str,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    if current_user and conv.user_id and conv.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    return conv


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: str,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found.")
    if current_user and conv.user_id and conv.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to delete this conversation.")
    db.delete(conv)
    db.commit()
