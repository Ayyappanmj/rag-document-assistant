"""Runs the evaluation dataset through the real RAG pipeline and saves evaluation/results.json.

Run from the project root, with the backend virtual environment active and Ollama running
(inside Docker:  docker compose exec backend python /evaluation/evaluate.py --ingest):

    python evaluation/evaluate.py --ingest        # first time: also indexes the sample PDFs
    python evaluation/evaluate.py                 # later runs
    python evaluation/evaluate.py --limit 5       # quick smoke test
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# In the Docker image the backend code lives in /app, not in <project>/backend.
BACKEND = Path(os.environ.get("RAG_BACKEND_DIR") or ROOT / "backend")
if not BACKEND.exists():
    BACKEND = Path("/app")

# The backend uses relative paths (sqlite:///./rag.db), so it must run from backend/ to share its database.
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

from app.config import get_settings  # noqa: E402
from app.core.logging import setup_logging  # noqa: E402
from app.models.database import SessionLocal, init_db  # noqa: E402
from app.rag import dependencies as deps  # noqa: E402
from app.services.chat_service import ChatService  # noqa: E402
from app.services.evaluation_service import (  # noqa: E402
    EvaluationSetupError, expected_document_names, ingest_sample_documents, load_questions,
    resolve_document_ids, run_evaluation,
)


def fmt(value: float | None, percent: bool = True) -> str:
    if value is None:
        return "-"
    return f"{value * 100:.0f}%" if percent else f"{value:.0f}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the RAG pipeline on questions.json")
    parser.add_argument("--ingest", action="store_true", help="index evaluation/sample_docs/*.pdf first")
    parser.add_argument("--limit", type=int, help="only run the first N questions")
    parser.add_argument("--top-k", type=int, help="override TOP_K")
    args = parser.parse_args()

    settings = get_settings()
    setup_logging("WARNING")  # keep the console readable
    init_db()

    try:
        all_questions = load_questions(settings.evaluation_dir)
    except EvaluationSetupError as exc:
        print(f"Error: {exc}")
        return 1

    if args.ingest:
        sample_dir = Path(settings.evaluation_dir) / "sample_docs"
        if not list(sample_dir.glob("*.pdf")):
            print("No sample PDFs found. Create them first:  python evaluation/make_sample_pdfs.py")
            return 1
        print("Indexing sample documents (the first run downloads the embedding model)...")
        added = ingest_sample_documents(SessionLocal, settings)
        print(f"  added: {', '.join(added) if added else 'nothing new, already indexed'}")

    with SessionLocal() as db:
        document_ids, missing = resolve_document_ids(db, expected_document_names(all_questions))
        if missing:
            print("Missing documents: " + ", ".join(missing))
            print("Run:  python evaluation/make_sample_pdfs.py  then  python evaluation/evaluate.py --ingest")
            return 1

        questions = all_questions[: args.limit] if args.limit else all_questions
        pipeline = ChatService(
            db, deps.get_hybrid_retriever(), deps.get_generator(), deps.get_grounding_evaluator(), settings
        )

        def progress(done: int, total: int) -> None:
            print(f"  [{done}/{total}] {questions[done - 1]['question'][:70]}")

        print(f"Evaluating {len(questions)} questions with {settings.llm_provider} ...")
        run = run_evaluation(db, pipeline, settings, questions, document_ids, args.top_k, progress)

    s = run["summary"]
    print("\n=== Sample Evaluation (heuristic scores, synthetic data, not a benchmark) ===")
    print(f"Questions: {s['total_questions']}  (answerable {s['answerable_questions']}, "
          f"unanswerable {s['unanswerable_questions']})")
    print(f"Faithfulness {fmt(s['faithfulness'])} | Answer relevance {fmt(s['answer_relevance'])} | "
          f"Context relevance {fmt(s['context_relevance'])} | Citation coverage {fmt(s['citation_coverage'])}")
    print(f"Retrieval precision {fmt(s['retrieval_precision'])} | Retrieval recall {fmt(s['retrieval_recall'])} | "
          f"Answer match {fmt(s['answer_match'])}")
    print(f"Correct refusals {fmt(s['refusal_accuracy'])} | False refusals {fmt(s['false_refusal_rate'])} | "
          f"Avg latency {fmt(s['avg_latency_ms'], False)} ms")
    print(f"Grounded {s['grounded_answers']} | Potentially hallucinated {s['potentially_hallucinated_answers']}")
    print(f"\nSaved: {Path(settings.evaluation_dir) / 'results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
