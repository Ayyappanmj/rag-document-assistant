# Backend tests

Install the test tools once (from `backend/`, virtual environment active):

    pip install -r requirements-dev.txt

Then run everything:

    pytest                                        # about 1 minute, no internet, no Ollama, no model download
    pytest --cov=app --cov-report=term-missing    # with a coverage report
    pytest tests/test_security.py -v              # one file
    pytest -k hybrid                              # tests whose name contains "hybrid"
    RUN_SLOW_TESTS=1 pytest                       # also runs the test that downloads the real embedding model
                                                  # (Windows PowerShell:  $env:RUN_SLOW_TESTS=1; pytest)

## How the tests stay fast and offline

* `tests/fakes.py` replaces the embedding model with a hashed bag-of-words vector: texts that share words get
  similar vectors, so retrieval tests are meaningful without downloading anything.
* `tests/conftest.py` gives every API test its own in-memory SQLite database, a temporary upload folder and a
  temporary FAISS index, so tests never touch your real data and never affect each other.
* LLM calls are replaced by tiny fake generators, or by `httpx.MockTransport` when testing the HTTP clients.

## What is covered

| Area | Files |
|---|---|
| PDF extraction | `test_document_processor.py`, `test_pdf_extraction_edge.py` |
| Chunking | `test_chunker.py`, `test_chunker_edge.py` |
| Embeddings | `test_embeddings.py` |
| FAISS vector search | `test_vector_store.py`, `test_vector_store_edge.py` |
| BM25 keyword search | `test_bm25_retriever.py`, `test_bm25_api.py` |
| Hybrid retrieval | `test_hybrid_retriever.py` (fusion maths), `test_hybrid_integration.py`, `test_hybrid_api.py` |
| Context building | `test_context_builder.py` |
| LLM clients and prompt | `test_generator.py` |
| Citations | `test_citation.py` |
| Hallucination detection | `test_evaluator.py`, grounding cases in `test_chat_api.py` |
| Evaluation metrics and runs | `test_eval_metrics.py`, `test_evaluation_api.py`, `test_dataset.py` |
| REST API | `test_documents_api.py`, `test_conversations_api.py`, `test_chat_api.py`, `test_dashboard_api.py`, `test_api_contract.py` |
| Security and privacy | `test_security.py` |

## Adding a test

Use the `client` fixture for anything that calls the API. Upload a real PDF with `make_pdf([(heading, body)])`
from `tests/conftest.py`. To control what the "LLM" says, monkeypatch `deps.get_generator`.
