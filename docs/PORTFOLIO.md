# Portfolio and resume text

## Portfolio description

Production-grade Retrieval-Augmented Generation platform for intelligent PDF question answering, combining FAISS
vector search and BM25 keyword retrieval with grounded LLM generation, source-level citations, and automated
hallucination evaluation.

## Resume bullet points

- Designed and built a Retrieval-Augmented Generation (RAG) platform in Python, FastAPI and Next.js that answers
  questions over multiple PDFs using hybrid search: Sentence Transformers semantic search on a FAISS vector index
  fused with BM25 keyword retrieval through configurable weighted scoring.
- Engineered grounded LLM generation with prompt engineering, retrieval thresholds, validated source citations and
  an automated hallucination detection check, plus an evaluation harness that measures faithfulness, answer
  relevance, citation coverage and retrieval precision and recall on a custom question set.
- Delivered a tested REST API with a TypeScript dashboard and chat interface, an automated pytest suite and CI, Docker
  Compose packaging and Vercel deployment, supporting local Ollama models or any OpenAI-compatible LLM provider.

Use these only for what you actually did, and do not add numbers (accuracy, latency, "X% fewer hallucinations")
unless you measured them yourself. Run `python evaluation/evaluate.py` and quote your own results, with the
dataset size and the fact that the scores are heuristics.

## ATS keywords covered

RAG, LLM, NLP, FAISS, BM25, Vector Search, Hybrid Search, Semantic Search, Python, FastAPI, Next.js,
Sentence Transformers, Prompt Engineering, Hallucination Detection, Evaluation, REST API, Docker, Vercel

## GitHub repository settings

- **About:** the portfolio description above.
- **Topics:** `rag`, `llm`, `nlp`, `faiss`, `bm25`, `hybrid-search`, `fastapi`, `nextjs`, `sentence-transformers`,
  `ollama`, `pdf`, `hallucination-detection`
- **Pin** the repository, and add the screenshots from `docs/screenshots/` to the README.

## Talking points for interviews

- Why hybrid search: dense vectors catch paraphrases, BM25 catches exact names, codes and numbers.
- Why a retrieval threshold: if nothing relevant is retrieved, the system refuses instead of letting the model guess.
- How the grounding check works and where it fails (heuristic, can miss subtle logic errors).
- What you would change for scale: managed vector database, hosted embeddings, authentication, streaming.
