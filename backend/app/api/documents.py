"""Document endpoints: upload, list, get, delete."""
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.core.security import get_optional_current_user
from app.models.database import Document, DocumentChunk, User, get_db, get_session_factory
from app.models.schemas import ChunkOut, DocumentOut
from app.rag import dependencies as deps
from app.services.document_service import process_document, recover_stale_documents

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

CHUNK = 1024 * 1024  # read uploads 1 MB at a time


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
    session_factory: sessionmaker = Depends(get_session_factory),
):
    settings = get_settings()
    original = Path(file.filename or "").name
    if not original.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF files are allowed.")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.pdf"
    dest = upload_dir / stored_name

    size = 0
    first = True
    try:
        with dest.open("wb") as out:
            while chunk := await file.read(CHUNK):
                if first:
                    if not chunk.startswith(b"%PDF"):  # check real content, not just extension
                        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "File is not a valid PDF.")
                    first = False
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        f"File exceeds the {settings.max_upload_mb} MB limit.",
                    )
                out.write(chunk)
        if size == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty.")
    except HTTPException:
        dest.unlink(missing_ok=True)
        raise

    doc = Document(
        user_id=current_user.id if current_user else None,
        name=original, stored_filename=stored_name, size_bytes=size,
        status="processing", embedding_model=settings.embedding_model,
    )
    db.add(doc)
    db.commit()
    logger.info("document_uploaded id=%s user_id=%s name=%s size_bytes=%d", doc.id, doc.user_id, doc.name, size)
    background_tasks.add_task(process_document, doc.id, session_factory)  # runs after the response
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    recover_stale_documents(db, force_all=False)
    query = select(Document)
    if current_user:
        query = query.where((Document.user_id == current_user.id) | (Document.user_id.is_(None)))
    else:
        query = query.where(Document.user_id.is_(None))
    return db.scalars(query.order_by(Document.created_at.desc())).all()


@router.post("/{document_id}/retry", response_model=DocumentOut)
def retry_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
    session_factory: sessionmaker = Depends(get_session_factory),
):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    if current_user and doc.user_id and doc.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to retry this document.")

    settings = get_settings()
    file_path = Path(settings.upload_dir) / doc.stored_filename
    if not file_path.exists():
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Original uploaded file is no longer available on the server. Please re-upload.",
        )

    doc.status = "processing"
    doc.error_message = None
    db.commit()
    db.refresh(doc)
    background_tasks.add_task(process_document, doc.id, session_factory)
    logger.info("document_retry_started id=%s", doc.id)
    return doc


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: str,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    recover_stale_documents(db, force_all=False)
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    if current_user and doc.user_id and doc.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    if not current_user and doc.user_id is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    return doc


@router.get("/{document_id}/chunks", response_model=list[ChunkOut])
def list_chunks(
    document_id: str,
    page: int | None = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    if current_user and doc.user_id and doc.user_id != current_user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    if not current_user and doc.user_id is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    query = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
    if page is not None:
        query = query.where(DocumentChunk.page_number == page)
    return db.scalars(query.order_by(DocumentChunk.chunk_index).offset(offset).limit(limit)).all()


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    if current_user and doc.user_id and doc.user_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized to delete this document.")
    (Path(get_settings().upload_dir) / doc.stored_filename).unlink(missing_ok=True)
    db.delete(doc)
    db.commit()
    removed = deps.get_vector_store().delete_document(document_id)  # drop its vectors too
    deps.get_bm25_retriever().invalidate()
    logger.info("document_vectors_removed id=%s count=%d", document_id, removed)
    logger.info("document_deleted id=%s", document_id)
