# Architecture

## System overview

```mermaid
flowchart TD
    U([User]) --> FE["Next.js Frontend<br/>(Vercel)"]
    FE -->|REST / JSON| API["FastAPI API"]
    API --> DP[Document Processing]
    DP --> PDF["PDF Extraction<br/>PyMuPDF, page numbers kept"]
    PDF --> CH["Chunking<br/>RecursiveCharacterTextSplitter"]
    CH --> EMB["Embeddings<br/>Sentence Transformers (all-MiniLM-L6-v2)"]
    CH --> BM["BM25 keyword index<br/>rank-bm25"]
    EMB --> FAISS[("FAISS vector index")]
    FAISS --> HR["Hybrid Retriever<br/>normalise + weighted fusion"]
    BM --> HR
    HR --> TH{"Evidence above<br/>threshold?"}
    TH -- no --> NO["'Insufficient evidence' reply<br/>(LLM is not called)"]
    TH -- yes --> CB[Context Builder]
    CB --> LLM["LLM<br/>Ollama or any OpenAI-compatible API"]
    LLM --> ANS[Grounded Answer]
    ANS --> CIT["Citation validation<br/>[Source N] to file + page"]
    CIT --> GR["Grounding check<br/>faithfulness, numbers, relevance"]
    GR --> OUT["Answer + citations + scores"]
    API --- DB[("SQLite<br/>documents, chunks, chats, evaluations")]
```

## One chat request

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as FastAPI
    participant R as Hybrid Retriever
    participant L as LLM
    participant G as Grounding check
    B->>A: POST /api/chat {question}
    A->>R: retrieve(question, top_k)
    R-->>A: ranked chunks (dense + BM25 scores)
    alt best cosine below RETRIEVAL_THRESHOLD
        A-->>B: "I couldn't find sufficient evidence..."
    else enough evidence
        A->>L: context-only prompt
        L-->>A: answer with [Source N] markers
        A->>A: validate and rewrite citations
        A->>G: answer + retrieved context
        G-->>A: grounded, confidence, unsupported claims
        A-->>B: answer, citations, scores, timings
    end
```

## Where the code lives

| Stage | File |
|---|---|
| PDF text and headings | `backend/app/rag/document_processor.py` |
| Chunking | `backend/app/rag/chunker.py` |
| Embeddings | `backend/app/rag/embeddings.py` |
| FAISS store | `backend/app/rag/vector_store.py` |
| BM25 | `backend/app/rag/bm25_retriever.py` |
| Hybrid fusion | `backend/app/rag/hybrid_retriever.py` |
| Context and prompt | `backend/app/rag/context_builder.py`, `prompt.py` |
| LLM clients | `backend/app/rag/generator.py` |
| Citations | `backend/app/rag/citation.py` |
| Hallucination check | `backend/app/rag/evaluator.py` |
| Chat orchestration | `backend/app/services/chat_service.py` |
| Evaluation runs | `backend/app/services/evaluation_service.py`, `evaluation/` |
