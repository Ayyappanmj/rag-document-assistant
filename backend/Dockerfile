# Backend image. Build context is the project root (see docker-compose.yml) so the evaluation/ folder can be
# included. Build it yourself with:  docker build -f backend/Dockerfile -t rag-backend .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/hf-cache \
    EVALUATION_DIR=/evaluation

# libgomp1 is the OpenMP runtime that FAISS needs on slim images
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies first, so code changes do not reinstall everything.
# CPU-only PyTorch is far smaller than the default (CUDA) build.
COPY backend/requirements.txt backend/requirements-chroma.txt ./
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt

# Optional second vector database. Build with it:  docker compose build --build-arg INSTALL_CHROMA=true backend
ARG INSTALL_CHROMA=false
RUN if [ "$INSTALL_CHROMA" = "true" ]; then pip install -r requirements-chroma.txt; fi

# Download the embedding model now, so the first upload does not need internet.
# Skip with:  docker compose build --build-arg PRELOAD_MODEL=false backend
ARG PRELOAD_MODEL=true
ARG EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RUN if [ "$PRELOAD_MODEL" = "true" ]; then \
      python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')"; \
    fi

COPY backend/app ./app
COPY evaluation /evaluation

# Run as a normal user, not root
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/data/uploads /app/data/indexes \
    && chown -R app:app /app /evaluation /opt/hf-cache
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)" || exit 1

# One worker on purpose: the FAISS index lives in memory, and several workers would each hold a different copy.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
