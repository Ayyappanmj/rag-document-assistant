"""Chat orchestration: retrieve -> threshold -> context -> generate -> cite -> grounding check -> persist.

`run_pipeline` does everything except saving, so the evaluation runner can reuse the exact same logic."""
import json
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.database import Citation, Conversation, Evaluation, Message
from app.models.schemas import ChatMetrics, ChatResponse, CitationOut
from app.rag.citation import process_citations
from app.rag.context_builder import build_context
from app.rag.evaluator import GroundingEvaluator, GroundingResult
from app.rag.generator import Generator, LLMError
from app.rag.hybrid_retriever import HybridResult, HybridRetriever
from app.rag.prompt import INSUFFICIENT_EVIDENCE, is_refusal

logger = logging.getLogger(__name__)


class ConversationNotFoundError(Exception):
    pass


@dataclass
class PipelineResult:
    answer: str
    metrics: ChatMetrics
    retrieved: list[HybridResult] = field(default_factory=list)  # everything retrieval returned
    sources: list[HybridResult] = field(default_factory=list)    # what is shown as citations
    best_similarity: float = 0.0
    refused: bool = True            # True = no answer was produced from the documents
    coverage: float | None = None
    invalid: list[int] = field(default_factory=list)
    grounding: GroundingResult | None = None
    answer_relevance: float | None = None
    context_relevance: float | None = None


class ChatService:
    def __init__(
        self, db: Session, retriever: HybridRetriever, generator: Generator,
        evaluator: GroundingEvaluator, settings: Settings,
    ):
        self._db, self._retriever, self._generator = db, retriever, generator
        self._evaluator, self._settings = evaluator, settings

    # ------------------------------------------------------------------ pipeline (no database writes)
    def run_pipeline(
        self, question: str, document_ids: list[str] | None = None, top_k: int | None = None,
    ) -> PipelineResult:
        started = time.perf_counter()

        # 1. Retrieve
        t0 = time.perf_counter()
        results = self._retriever.retrieve(question, top_k or self._settings.top_k, document_ids)
        retrieval_ms = (time.perf_counter() - t0) * 1000

        # 2. Retrieval threshold: no strong semantic match -> do not call the LLM at all.
        # The raw cosine (dense_score) is used because the fused score is only relative.
        best_similarity = max((r.dense_score or 0.0 for r in results), default=0.0)
        has_evidence = bool(results) and best_similarity >= self._settings.retrieval_threshold

        out = PipelineResult(
            answer=INSUFFICIENT_EVIDENCE, metrics=ChatMetrics(
                retrieval_time_ms=0, generation_time_ms=0, total_time_ms=0, evaluation_time_ms=0),
            retrieved=results, best_similarity=best_similarity,
        )
        generation_ms = evaluation_ms = 0.0

        if has_evidence:
            context = build_context(results, self._settings.max_context_chars)
            t1 = time.perf_counter()
            raw_answer = self._generator.generate(question, context.text)  # may raise LLMError
            generation_ms = (time.perf_counter() - t1) * 1000

            if is_refusal(raw_answer):
                out.answer = raw_answer  # the model declined: no claims to cite or verify
            else:
                out.refused = False
                # 3. Citations: validate [Source N] markers and rewrite them.
                checked = process_citations(raw_answer, context.sources)
                out.answer, out.coverage, out.invalid = checked.answer, checked.coverage, checked.invalid_numbers
                # Show only sources the answer cites; if it cited none, show the retrieved evidence instead
                # so the user can still verify (coverage 0 flags the missing citations).
                out.sources = checked.cited_sources or context.sources

                # 4. Grounding check against everything the model was shown. Never fails the request.
                t2 = time.perf_counter()
                try:
                    grounding = self._evaluator.evaluate(out.answer, [s.text for s in context.sources])
                    out.answer_relevance = round(self._evaluator.answer_relevance(question, out.answer), 3)
                    sims = [max(0.0, s.dense_score) for s in context.sources if s.dense_score is not None]
                    out.context_relevance = round(sum(sims) / len(sims), 3) if sims else None
                    if out.invalid and grounding.grounded:
                        grounding.grounded = False  # the model cited sources it was never given
                    out.grounding = grounding
                except Exception:
                    logger.exception("grounding_check_failed")
                evaluation_ms = (time.perf_counter() - t2) * 1000

                if self._settings.block_ungrounded and out.grounding and out.grounding.grounded is False:
                    out.answer, out.sources, out.refused = INSUFFICIENT_EVIDENCE, [], True  # safeguard

        out.metrics = ChatMetrics(
            retrieval_time_ms=round(retrieval_ms, 1),
            generation_time_ms=round(generation_ms, 1),
            total_time_ms=round((time.perf_counter() - started) * 1000, 1),
            evaluation_time_ms=round(evaluation_ms, 1),
        )
        return out

    # ------------------------------------------------------------------ chat (pipeline + persistence)
    def answer(
        self, question: str, conversation_id: str | None = None,
        document_ids: list[str] | None = None, top_k: int | None = None,
        regenerate: bool = False, user_id: str | None = None,
    ) -> ChatResponse:
        asked_at = datetime.now(timezone.utc)
        conversation = None
        if conversation_id:
            conversation = self._db.get(Conversation, conversation_id)
            if conversation is None:
                raise ConversationNotFoundError(conversation_id)

        r = self.run_pipeline(question, document_ids, top_k)
        grounding = r.grounding
        grounded = grounding.grounded if grounding else None
        confidence = grounding.confidence if grounding and grounding.grounded is not None else None
        faithfulness = grounding.faithfulness if grounding and grounding.grounded is not None else None
        unsupported = grounding.unsupported_claims if grounding else []

        # Persist everything in one transaction (nothing is saved if retrieval/generation failed).
        if conversation is None:
            title = question[:60] + ("…" if len(question) > 60 else "")
            conversation = Conversation(title=title, user_id=user_id)
            self._db.add(conversation)
            self._db.flush()
        if regenerate:
            self._remove_last_exchange(conversation.id, question)  # only after a successful new answer
        user_msg = Message(conversation_id=conversation.id, role="user", content=question, created_at=asked_at)
        assistant = Message(
            conversation_id=conversation.id, role="assistant", content=r.answer,
            grounded=grounded, confidence=confidence,
            metrics={
                **r.metrics.model_dump(), "citation_coverage": r.coverage, "invalid_citations": r.invalid,
                "faithfulness": faithfulness, "answer_relevance": r.answer_relevance,
                "context_relevance": r.context_relevance, "unsupported_claims": unsupported,
            },
        )
        assistant.citations = [
            Citation(
                document_id=s.document_id, document_name=s.document_name, page=s.page_number,
                chunk_id=s.chunk_id, text=s.text,
                score=s.dense_score if s.dense_score is not None else s.score,  # cosine similarity when known
                retrieval_type="hybrid",
            )
            for s in r.sources
        ]
        self._db.add_all([user_msg, assistant])
        self._db.flush()
        if grounding is not None or r.answer_relevance is not None:  # only answers that were actually generated
            self._db.add(Evaluation(
                message_id=assistant.id, question=question, faithfulness=faithfulness,
                answer_relevance=r.answer_relevance, context_relevance=r.context_relevance,
                citation_coverage=r.coverage, latency_ms=r.metrics.total_time_ms, is_sample=False,
            ))
        self._db.commit()

        # Log counts and timings only: never the question or answer text.
        logger.info(
            "chat_answered retrieved=%d shown=%d grounded=%s confidence=%s coverage=%s invalid_citations=%d "
            "best_similarity=%.2f retrieval_ms=%.0f generation_ms=%.0f evaluation_ms=%.0f",
            len(r.retrieved), len(r.sources), grounded, confidence, r.coverage, len(r.invalid),
            r.best_similarity, r.metrics.retrieval_time_ms, r.metrics.generation_time_ms,
            r.metrics.evaluation_time_ms,
        )
        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant.id,
            answer=r.answer,
            grounded=grounded,
            confidence=confidence,
            faithfulness=faithfulness,
            answer_relevance=r.answer_relevance,
            context_relevance=r.context_relevance,
            unsupported_claims=unsupported,
            citations=[CitationOut.model_validate(c) for c in assistant.citations],
            citation_coverage=r.coverage,
            invalid_citations=r.invalid,
            metrics=r.metrics,
        )

    def stream_answer(
        self, question: str, conversation_id: str | None = None,
        document_ids: list[str] | None = None, top_k: int | None = None,
        regenerate: bool = False, user_id: str | None = None,
    ) -> Iterator[str]:
        started = time.perf_counter()
        asked_at = datetime.now(timezone.utc)

        conversation = None
        if conversation_id:
            conversation = self._db.get(Conversation, conversation_id)
            if conversation is None:
                raise ConversationNotFoundError(conversation_id)

        # 1. Retrieve
        t0 = time.perf_counter()
        results = self._retriever.retrieve(question, top_k or self._settings.top_k, document_ids)
        retrieval_ms = (time.perf_counter() - t0) * 1000

        best_similarity = max((r.dense_score or 0.0 for r in results), default=0.0)
        has_evidence = bool(results) and best_similarity >= self._settings.retrieval_threshold

        if not has_evidence:
            yield f"data: {json.dumps({'type': 'token', 'token': INSUFFICIENT_EVIDENCE})}\n\n"

            if conversation is None:
                title = question[:60] + ("…" if len(question) > 60 else "")
                conversation = Conversation(title=title, user_id=user_id)
                self._db.add(conversation)
                self._db.flush()
            if regenerate:
                self._remove_last_exchange(conversation.id, question)

            user_msg = Message(conversation_id=conversation.id, role="user", content=question, created_at=asked_at)
            metrics = ChatMetrics(
                retrieval_time_ms=round(retrieval_ms, 1),
                generation_time_ms=0.0,
                total_time_ms=round((time.perf_counter() - started) * 1000, 1),
                evaluation_time_ms=0.0,
            )
            assistant = Message(
                conversation_id=conversation.id, role="assistant", content=INSUFFICIENT_EVIDENCE,
                grounded=None, confidence=None,
                metrics=metrics.model_dump(),
            )
            self._db.add_all([user_msg, assistant])
            self._db.commit()

            resp = ChatResponse(
                conversation_id=conversation.id,
                message_id=assistant.id,
                answer=INSUFFICIENT_EVIDENCE,
                citations=[],
                metrics=metrics,
            )
            yield f"data: {json.dumps({'type': 'done', 'response': resp.model_dump(mode='json')})}\n\n"
            return

        # 2. Context and sources
        context = build_context(results, self._settings.max_context_chars)
        sources_payload = [
            CitationOut(
                document_id=s.document_id,
                document_name=s.document_name,
                page=s.page_number,
                chunk_id=s.chunk_id,
                text=s.text,
                score=s.dense_score if s.dense_score is not None else s.score,
                retrieval_type="hybrid",
            ).model_dump(mode="json")
            for s in context.sources
        ]
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources_payload})}\n\n"

        # 3. Stream from LLM
        t1 = time.perf_counter()
        token_chunks: list[str] = []
        try:
            for chunk in self._generator.generate_stream(question, context.text):
                token_chunks.append(chunk)
                yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"
        except LLMError as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
            return

        generation_ms = (time.perf_counter() - t1) * 1000
        raw_answer = "".join(token_chunks).strip()

        # 4. Citations & Grounding
        evaluation_ms = 0.0
        grounding = None
        grounded = None
        confidence = None
        faithfulness = None
        unsupported = []
        answer_relevance = None
        context_relevance = None
        coverage = None
        invalid = []
        sources = context.sources
        final_answer = raw_answer

        if not is_refusal(raw_answer):
            checked = process_citations(raw_answer, context.sources)
            final_answer, coverage, invalid = checked.answer, checked.coverage, checked.invalid_numbers
            sources = checked.cited_sources or context.sources

            t2 = time.perf_counter()
            try:
                grounding = self._evaluator.evaluate(final_answer, [s.text for s in context.sources])
                answer_relevance = round(self._evaluator.answer_relevance(question, final_answer), 3)
                sims = [max(0.0, s.dense_score) for s in context.sources if s.dense_score is not None]
                context_relevance = round(sum(sims) / len(sims), 3) if sims else None
                if invalid and grounding.grounded:
                    grounding.grounded = False
                grounded = grounding.grounded
                confidence = grounding.confidence
                faithfulness = grounding.faithfulness
                unsupported = grounding.unsupported_claims
            except Exception:
                logger.exception("grounding_check_failed")
            evaluation_ms = (time.perf_counter() - t2) * 1000

            if self._settings.block_ungrounded and grounding and grounding.grounded is False:
                final_answer, sources = INSUFFICIENT_EVIDENCE, []

        metrics = ChatMetrics(
            retrieval_time_ms=round(retrieval_ms, 1),
            generation_time_ms=round(generation_ms, 1),
            total_time_ms=round((time.perf_counter() - started) * 1000, 1),
            evaluation_time_ms=round(evaluation_ms, 1),
        )

        # 5. Persist to DB
        if conversation is None:
            title = question[:60] + ("…" if len(question) > 60 else "")
            conversation = Conversation(title=title, user_id=user_id)
            self._db.add(conversation)
            self._db.flush()
        if regenerate:
            self._remove_last_exchange(conversation.id, question)

        user_msg = Message(conversation_id=conversation.id, role="user", content=question, created_at=asked_at)
        assistant = Message(
            conversation_id=conversation.id, role="assistant", content=final_answer,
            grounded=grounded, confidence=confidence,
            metrics={
                **metrics.model_dump(), "citation_coverage": coverage, "invalid_citations": invalid,
                "faithfulness": faithfulness, "answer_relevance": answer_relevance,
                "context_relevance": context_relevance, "unsupported_claims": unsupported,
            },
        )
        assistant.citations = [
            Citation(
                document_id=s.document_id, document_name=s.document_name, page=s.page_number,
                chunk_id=s.chunk_id, text=s.text,
                score=s.dense_score if s.dense_score is not None else s.score,
                retrieval_type="hybrid",
            )
            for s in sources
        ]
        self._db.add_all([user_msg, assistant])
        self._db.flush()
        if grounding is not None or answer_relevance is not None:
            self._db.add(Evaluation(
                message_id=assistant.id, question=question, faithfulness=faithfulness,
                answer_relevance=answer_relevance, context_relevance=context_relevance,
                citation_coverage=coverage, latency_ms=metrics.total_time_ms, is_sample=False,
            ))
        self._db.commit()

        # 6. Yield final done event
        chat_resp = ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant.id,
            answer=final_answer,
            grounded=grounded,
            confidence=confidence,
            faithfulness=faithfulness,
            answer_relevance=answer_relevance,
            context_relevance=context_relevance,
            unsupported_claims=unsupported,
            citations=[CitationOut.model_validate(c) for c in assistant.citations],
            citation_coverage=coverage,
            invalid_citations=invalid,
            metrics=metrics,
        )
        yield f"data: {json.dumps({'type': 'done', 'response': chat_resp.model_dump(mode='json')})}\n\n"

    def _remove_last_exchange(self, conversation_id: str, question: str) -> None:
        """Delete the newest user+assistant pair if it matches this question (used by "regenerate")."""
        last_two = self._db.scalars(
            select(Message).where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc()).limit(2)
        ).all()
        if len(last_two) != 2 or last_two[0].role != "assistant" or last_two[1].role != "user":
            return
        if last_two[1].content != question:
            return
        ids = [m.id for m in last_two]
        # Explicit deletes: do not rely on database-level cascades.
        self._db.execute(delete(Evaluation).where(Evaluation.message_id.in_(ids)))
        self._db.execute(delete(Citation).where(Citation.message_id.in_(ids)))
        self._db.execute(delete(Message).where(Message.id.in_(ids)))
        self._db.flush()
