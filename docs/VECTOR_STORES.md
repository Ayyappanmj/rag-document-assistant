# Vector databases: FAISS and Chroma

The app can keep its embeddings in either of two free, open-source vector databases. Both run inside the backend
process (no extra server), both are searched the same way by the hybrid retriever, and you pick one with a setting.

| | FAISS (default) | Chroma (optional) |
|---|---|---|
| What it is | A similarity-search library from Meta | A vector database with its own storage |
| Search used here | Flat index: compares the query with every vector, so results are exact | HNSW graph: approximate nearest-neighbour search |
| Metadata filter (by document) | Not built in. This project searches everything, then filters | Built in (`where` filter inside the database) |
| Saving to disk | Manual. This project writes `faiss.index` and a JSON sidecar after each change | Automatic, in its own folder |
| Stores chunk text and page numbers | In the JSON sidecar written by this project | In the database itself |
| Deleting a document | `IndexIDMap2.remove_ids` | `delete` by id |
| Install size | Small | Larger (more dependencies), so it is optional |
| Telemetry | None | Anonymous telemetry is switched off in this project's code |

Facts about Chroma (HNSW for single-node, `space` option, metadata filters, `cosine` returning distance) come
from [Chroma's documentation](https://docs.trychroma.com/docs/collections/configure). This table says how each
database *works*. How fast or accurate each one is **on your machine** is what the benchmark below measures.

## Switch the database

1. Install Chroma (once): `pip install -r backend/requirements-chroma.txt`
2. In `backend/.env` set `VECTOR_STORE=chroma` (or `faiss`).
3. The new database starts empty, so fill it from the chunks already saved in SQLite. Stop the server, then from
   `backend/`:

       python -m app.scripts.reindex

   Only the embeddings are recomputed (the chunk text is already stored). Run it again at any time; it never
   duplicates vectors. You can also pass `--store chroma` or `--store faiss` to fill one explicitly.
4. Start the backend. The Settings page shows which database is active.

Documents you upload after switching go straight into the active database. The same `reindex` command also
rebuilds a FAISS index that was lost (for example on a host with a temporary disk).

Docker: set `INSTALL_CHROMA=true` and `VECTOR_STORE=chroma` in `.env`, then `docker compose up --build`.
Chroma's files live in the `rag_data` volume (`/app/data/chroma`).

## Compare them

From the project root, with the backend virtual environment active:

    pip install -r backend/requirements-chroma.txt
    python evaluation/compare_vector_stores.py                  # synthetic vectors
    python evaluation/compare_vector_stores.py --vectors 5000 --queries 100     # quicker
    python evaluation/compare_vector_stores.py --real           # also use your indexed PDFs

`--real` needs the sample documents indexed (`python evaluation/evaluate.py --ingest`) and loads the embedding model.
Results are saved to `evaluation/vector_store_comparison.json` and shown on the **Evaluation** page.

What is measured, per database, with the identical vectors:

| Measure | Meaning |
|---|---|
| Build time | Adding every vector, including saving to disk |
| Disk size | Size of the saved index folder |
| Reopen time | Opening the saved index again, as after a restart |
| Query time (median, 95th percentile) | Per-query latency for top-k search, after a short warm-up |
| Filtered query time | Same, restricted to a few documents |
| Recall at k vs exact | Share of the true nearest neighbours returned, checked against brute-force numpy |
| Filtered recall at k | The same check for filtered searches |
| Delete one document | Time to remove one document's vectors |

With `--real`, both databases are filled with your actual chunks and asked the evaluation questions. That adds
retrieval precision and recall (document level), average query time, and how often both returned the same passages.

## Reading the results honestly

- Numbers come from one run on one machine. Another computer, another vector count, or a different dimension can
  change the picture. Run it with sizes close to what you plan to use.
- FAISS flat search is exact, so its recall is 1.0 by construction. That measures correctness of the code, not speed.
  Chroma's HNSW trades a little accuracy for speed on large collections. On a small collection it may be exact too.
- FAISS build time here includes this project saving the index and its JSON sidecar after every batch. Chroma saves
  as it goes. Both are real costs of the two designs as implemented here.
- Filtered search is where the designs differ most: this project's FAISS store scans all vectors and then filters,
  while Chroma filters inside the database. Compare the "Filtered query" rows at a vector count that matters to you.
- Memory use is not measured.
- Do not quote the numbers as a general ranking of the two libraries. Quote them as "measured on my laptop with N
  vectors", with the parameters from the JSON file.

## Hypotheses to test (not results)

Before you run it, write down what you expect, then check. Sensible things to expect from the designs above:

1. FAISS recall is exactly 1.0. Chroma recall is 1.0 or slightly below.
2. Filtered queries grow slower with collection size on FAISS than on Chroma.
3. Chroma's folder is larger than FAISS's on disk because it stores text and metadata too.
4. On the real PDFs both return nearly the same passages, so answer quality barely changes.

If a result surprises you, that is the interesting part to explain in an interview.

## How it is built

- `app/rag/vector_types.py` defines `VectorIndex`, the small interface both databases implement
  (`add`, `search`, `delete_document`, `count`).
- `app/rag/vector_store.py` is the FAISS implementation, `app/rag/chroma_store.py` the Chroma one.
- `app/rag/vector_factory.py` picks one from `VECTOR_STORE`. Nothing else in the app knows which is active.
- `tests/test_vector_store_contract.py` runs the same tests against both, and `tests/test_chroma_api.py` runs the
  whole upload, search, chat and delete flow on Chroma.
- `app/services/vector_benchmark.py` and `evaluation/compare_vector_stores.py` produce the comparison.
