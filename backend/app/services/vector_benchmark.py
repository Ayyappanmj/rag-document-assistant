"""Measures FAISS and Chroma side by side on the same vectors. Nothing here is hard-coded: every number in the
output comes from running the code on your machine, so results differ between computers."""
import importlib.metadata
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np

from app.rag.chunker import Chunk
from app.rag.eval_metrics import retrieval_precision_recall
from app.rag.vector_types import VectorIndex

LABEL = "Vector store benchmark"
NOTE = (
    "Timings come from one run on one machine. Synthetic vectors (clustered, normalised) measure speed and "
    "approximation error; the real-documents section measures retrieval on your own indexed PDFs. "
    "Not a general benchmark of either library."
)
BATCH = 1000
CHUNKS_PER_DOC = 100

StoreFactory = Callable[[Path], VectorIndex]


# ------------------------------------------------------------------ data
def make_dataset(vectors: int, dimension: int, queries: int, seed: int, clusters: int = 50):
    rng = np.random.default_rng(seed)
    centers = rng.normal(size=(clusters, dimension))
    base = centers[rng.integers(0, clusters, size=vectors)] + 0.6 * rng.normal(size=(vectors, dimension))
    base = (base / np.linalg.norm(base, axis=1, keepdims=True)).astype("float32")
    picks = base[rng.integers(0, vectors, size=queries)]
    qs = picks + 0.3 * rng.normal(size=picks.shape).astype("float32")
    qs = (qs / np.linalg.norm(qs, axis=1, keepdims=True)).astype("float32")
    chunks = [
        Chunk(f"c{i}", f"doc{i // CHUNKS_PER_DOC}", f"doc{i // CHUNKS_PER_DOC}.pdf", i % 50 + 1, i, f"synthetic chunk {i}")
        for i in range(vectors)
    ]
    return chunks, base, qs


def exact_top_k(vectors: np.ndarray, queries: np.ndarray, ids: list[str], k: int) -> list[list[str]]:
    """Brute-force ground truth with plain numpy."""
    sims = queries @ vectors.T
    k = min(k, vectors.shape[0])
    top = np.argpartition(-sims, k - 1, axis=1)[:, :k]
    ordered = np.take_along_axis(top, np.argsort(-np.take_along_axis(sims, top, axis=1), axis=1), axis=1)
    return [[ids[j] for j in row] for row in ordered]


def _recall(found: list[list[str]], truth: list[list[str]]) -> float:
    scores = [len(set(f) & set(t)) / len(t) for f, t in zip(found, truth) if t]
    return round(float(np.mean(scores)), 4) if scores else 0.0


def _latency(ms: list[float]) -> dict:
    return {"mean": round(float(np.mean(ms)), 3), "p50": round(float(np.percentile(ms, 50)), 3),
            "p95": round(float(np.percentile(ms, 95)), 3)}


def _disk_mb(path: Path) -> float:
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return round(total / (1024 * 1024), 2)


# ------------------------------------------------------------------ one store
def benchmark_store(
    make_store: StoreFactory, path: Path, chunks: list[Chunk], vectors: np.ndarray, queries: np.ndarray,
    top_k: int, filter_docs: list[str],
) -> dict:
    ids = [c.chunk_id for c in chunks]
    truth = exact_top_k(vectors, queries, ids, top_k)
    wanted = set(filter_docs)
    sub_idx = [i for i, c in enumerate(chunks) if c.document_id in wanted]
    allowed_ids = {ids[i] for i in sub_idx}
    filtered_truth = [
        [ids[sub_idx[j]] for j in row] for row in np.argsort(-(queries @ vectors[sub_idx].T), axis=1)[:, :top_k]
    ]

    store = make_store(path)
    t0 = time.perf_counter()
    for start in range(0, len(chunks), BATCH):
        store.add(chunks[start:start + BATCH], vectors[start:start + BATCH])
    build_seconds = time.perf_counter() - t0
    disk_mb = _disk_mb(path)

    for q in queries[:10]:  # warm-up, not measured
        store.search(q, top_k)

    times, found = [], []
    for q in queries:
        t = time.perf_counter()
        found.append([r.chunk_id for r in store.search(q, top_k)])
        times.append((time.perf_counter() - t) * 1000)

    ftimes, ffound = [], []
    for q in queries:
        t = time.perf_counter()
        ffound.append([r.chunk_id for r in store.search(q, top_k, filter_docs)])
        ftimes.append((time.perf_counter() - t) * 1000)
    filter_ok = all(cid in allowed_ids for row in ffound for cid in row)

    del store
    t = time.perf_counter()
    reopened = make_store(path)
    open_seconds = time.perf_counter() - t
    reopened_count = reopened.count

    t = time.perf_counter()
    removed = reopened.delete_document(chunks[0].document_id)
    delete_ms = (time.perf_counter() - t) * 1000

    return {
        "index_type": reopened.index_type,
        "build_seconds": round(build_seconds, 3),
        "vectors_per_second": round(len(chunks) / build_seconds) if build_seconds > 0 else None,
        "disk_mb": disk_mb,
        "open_seconds": round(open_seconds, 3),
        "reopened_vectors": reopened_count,
        "query_ms": _latency(times),
        "filtered_query_ms": _latency(ftimes),
        "recall_at_k": _recall(found, truth),
        "filtered_recall_at_k": _recall(ffound, filtered_truth),
        "filter_correct": bool(filter_ok),
        "delete_document_ms": round(delete_ms, 3),
        "deleted_vectors": removed,
    }


# ------------------------------------------------------------------ real documents
def compare_on_real_documents(
    db, embedder, questions: list[dict], document_ids: list[str] | None, top_k: int,
    factories: dict[str, StoreFactory], root: Path,
) -> dict:
    """Fills every store from the chunks in the database, then asks the evaluation questions."""
    from app.services.reindex_service import reindex_documents

    stores: dict[str, VectorIndex] = {}
    for name, make in factories.items():
        stores[name] = make(root / f"real-{name}")
        reindex_documents(db, embedder, stores[name])
    vectors = embedder.embed_texts([q["question"] for q in questions])

    per_store: dict[str, dict] = {}
    top_sets: dict[str, list[set[str]]] = {}
    for name, store in stores.items():
        precisions, recalls, times, sets = [], [], [], []
        for q, vec in zip(questions, vectors):
            t = time.perf_counter()
            results = store.search(vec, top_k, document_ids)
            times.append((time.perf_counter() - t) * 1000)
            sets.append({r.chunk_id for r in results})
            p, r = retrieval_precision_recall([x.document_name for x in results], q.get("expected_sources", []))
            if p is not None:
                precisions.append(p)
                recalls.append(r)
        top_sets[name] = sets
        per_store[name] = {
            "retrieval_precision": round(float(np.mean(precisions)), 3) if precisions else None,
            "retrieval_recall": round(float(np.mean(recalls)), 3) if recalls else None,
            "avg_query_ms": round(float(np.mean(times)), 3) if times else None,
            "vectors": store.count,
        }
    overlap = None
    if len(top_sets) == 2:
        a, b = list(top_sets.values())
        pairs = [len(x & y) / len(x | y) for x, y in zip(a, b) if x | y]
        overlap = round(float(np.mean(pairs)), 3) if pairs else None
    return {"questions": len(questions), "top_k": top_k, "stores": per_store, "top_k_overlap_jaccard": overlap}


# ------------------------------------------------------------------ whole run
def _version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def run_benchmark(
    factories: dict[str, StoreFactory], work_dir: Path, vectors: int = 20000, dimension: int = 384,
    queries: int = 200, top_k: int = 5, seed: int = 42, progress: Callable[[str], None] = lambda _: None,
) -> dict:
    chunks, data, qs = make_dataset(vectors, dimension, queries, seed)
    docs = sorted({c.document_id for c in chunks})
    filter_docs = [str(d) for d in np.random.default_rng(seed).choice(docs, size=min(3, len(docs)), replace=False)]

    results: dict[str, dict] = {}
    for name, make in factories.items():
        progress(f"benchmarking {name} ...")
        try:
            results[name] = benchmark_store(make, work_dir / name, chunks, data, qs, top_k, filter_docs)
        except ImportError as exc:  # optional dependency (chromadb) not installed
            results[name] = {"error": str(exc)}
    return {
        "label": LABEL,
        "note": NOTE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": sys.version.split()[0], "platform": platform.platform(), "cpu_count": os.cpu_count(),
            "faiss": _version("faiss-cpu"), "chromadb": _version("chromadb"), "numpy": _version("numpy"),
        },
        "parameters": {"vectors": vectors, "dimension": dimension, "queries": queries, "top_k": top_k,
                       "seed": seed, "filter_documents": len(filter_docs), "documents": len(docs)},
        "stores": results,
    }
