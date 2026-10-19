"""Compares FAISS and Chroma and saves evaluation/vector_store_comparison.json.

Run from the project root with the backend virtual environment active:

    pip install -r backend/requirements-chroma.txt          # once, Chroma is optional
    python evaluation/compare_vector_stores.py              # synthetic vectors, a minute or two
    python evaluation/compare_vector_stores.py --vectors 5000 --queries 100     # quicker
    python evaluation/compare_vector_stores.py --real       # also test on your indexed PDFs (loads the model)
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = Path(os.environ.get("RAG_BACKEND_DIR") or ROOT / "backend")
if not BACKEND.exists():
    BACKEND = Path("/app")
os.chdir(BACKEND)  # the backend uses relative paths such as sqlite:///./rag.db
sys.path.insert(0, str(BACKEND))

from app.config import get_settings  # noqa: E402
from app.core.logging import setup_logging  # noqa: E402
from app.rag.vector_store import VectorStore  # noqa: E402
from app.services.vector_benchmark import compare_on_real_documents, run_benchmark  # noqa: E402


def factories():
    makers = {"faiss": lambda path: VectorStore(path)}
    try:
        from app.rag.chroma_store import ChromaVectorStore
        makers["chroma"] = lambda path: ChromaVectorStore(path)
    except ImportError:
        print("chromadb is not installed, so only FAISS will be measured. "
              "Install it with: pip install -r backend/requirements-chroma.txt")
    return makers


def row(label: str, a, b, unit: str = "") -> None:
    print(f"{label:<30}{str(a) + unit:>16}{str(b) + unit:>16}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare FAISS and Chroma")
    parser.add_argument("--vectors", type=int, default=20000)
    parser.add_argument("--dimension", type=int, default=384)
    parser.add_argument("--queries", type=int, default=200)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--real", action="store_true", help="also compare on the PDFs indexed in the database")
    args = parser.parse_args()

    settings = get_settings()
    setup_logging("WARNING")
    makers = factories()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        result = run_benchmark(
            makers, tmp_path, args.vectors, args.dimension, args.queries, args.top_k, args.seed,
            progress=lambda message: print(f"  {message}"),
        )

        if args.real:
            from app.models.database import SessionLocal, init_db
            from app.rag.embeddings import EmbeddingService
            from app.services.evaluation_service import (
                expected_document_names, load_questions, resolve_document_ids,
            )

            init_db()
            questions = load_questions(settings.evaluation_dir)
            embedder = EmbeddingService(settings.embedding_model, settings.embedding_batch_size)
            with SessionLocal() as db:
                ids, missing = resolve_document_ids(db, expected_document_names(questions))
                if missing:
                    print("Skipping --real, missing documents: " + ", ".join(missing))
                    print("Run: python evaluation/evaluate.py --ingest")
                else:
                    print("  comparing on your indexed documents ...")
                    result["real_documents"] = compare_on_real_documents(
                        db, embedder, questions, ids, args.top_k, makers, tmp_path
                    )

    out = Path(settings.evaluation_dir) / "vector_store_comparison.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    p = result["parameters"]
    print(f"\n=== {p['vectors']} vectors, {p['dimension']} dimensions, {p['queries']} queries, top-{p['top_k']} ===")
    stores = result["stores"]
    names = list(stores)
    ok = [n for n in names if "error" not in stores[n]]
    print(f"{'':<30}" + "".join(f"{n:>16}" for n in ok))
    fields = [
        ("Index type", lambda s: s["index_type"], ""),
        ("Build time (s)", lambda s: s["build_seconds"], ""),
        ("Disk (MB)", lambda s: s["disk_mb"], ""),
        ("Reopen time (s)", lambda s: s["open_seconds"], ""),
        ("Query p50 (ms)", lambda s: s["query_ms"]["p50"], ""),
        ("Query p95 (ms)", lambda s: s["query_ms"]["p95"], ""),
        ("Filtered query p50 (ms)", lambda s: s["filtered_query_ms"]["p50"], ""),
        ("Recall@k vs exact", lambda s: s["recall_at_k"], ""),
        ("Filtered recall@k", lambda s: s["filtered_recall_at_k"], ""),
        ("Delete document (ms)", lambda s: s["delete_document_ms"], ""),
    ]
    for label, get, unit in fields:
        print(f"{label:<30}" + "".join(f"{str(get(stores[n]) ) + unit:>16}" for n in ok))
    for n in names:
        if "error" in stores[n]:
            print(f"{n}: skipped ({stores[n]['error']})")
    if "real_documents" in result:
        print("\nOn your documents:", json.dumps(result["real_documents"], indent=2))
    print(f"\nSaved: {out}")
    print("These numbers describe this machine and this run only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
