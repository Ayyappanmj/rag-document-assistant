# Running with Docker

## First time

1. Install Docker Desktop (Windows/macOS) or Docker Engine with the Compose plugin (Linux), and start it.
2. Install Ollama (https://ollama.com) on your computer and download a model once: `ollama pull llama3.2`
3. Copy the settings file (in the project root):

   - Windows (PowerShell): `copy .env.example .env`
   - macOS / Linux: `cp .env.example .env`

4. Start everything:

       docker compose up --build

   The first build takes several minutes (it downloads PyTorch and the embedding model). Later starts take seconds.

5. Open http://localhost:3000 (app) and http://localhost:8000/docs (API documentation).

Stop with `Ctrl+C`, or `docker compose down` (your data is kept). `docker compose down -v` also deletes all
uploaded documents, indexes, conversations and evaluation results.

## Run Ollama inside Docker too (optional)

    docker compose --profile ollama up --build
    docker compose exec ollama ollama pull llama3.2

and add `DOCKER_OLLAMA_URL=http://ollama:11434` to your `.env`. This runs on CPU only, so it is slower than
Ollama installed directly on your computer.

## Useful commands

    docker compose logs -f backend          # watch the backend logs
    docker compose ps                       # status and health of each service
    docker compose restart backend          # restart after changing .env
    docker compose build --no-cache         # rebuild from scratch

## Running the sample evaluation in Docker

    docker compose exec backend python /evaluation/make_sample_pdfs.py
    docker compose exec backend python /evaluation/evaluate.py --ingest
    docker compose restart backend          # so the running server loads the newly indexed documents

Then open http://localhost:3000/evaluation.

## Using Chroma instead of FAISS (optional)

In `.env` set `INSTALL_CHROMA=true` and `VECTOR_STORE=chroma`, then `docker compose up --build`. The new database starts
empty, so fill it from the saved chunks (this recomputes the embeddings):

    docker compose exec backend python -m app.scripts.reindex
    docker compose restart backend

To compare the two databases inside the container:
`docker compose exec backend python /evaluation/compare_vector_stores.py` (build with `INSTALL_CHROMA=true`).
More in [docs/VECTOR_STORES.md](docs/VECTOR_STORES.md).

## Without Docker (what you used while developing)

Terminal 1, backend (from `backend/`):

    python -m venv .venv
    .venv\Scripts\activate                  # macOS/Linux: source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload

Terminal 2, frontend (from `frontend/`):

    npm install
    npm run dev

Tests: `pip install -r requirements-dev.txt` then `pytest` (from `backend/`).

## Troubleshooting

| Problem | Fix |
|---|---|
| Chat says "Could not reach the language model server" | Ollama is not running. Start it, or check `DOCKER_OLLAMA_URL`. On Linux the backend reaches the host through `host.docker.internal`, which `docker-compose.yml` already maps. |
| Browser shows "Cannot reach the backend" | `NEXT_PUBLIC_API_URL` must be an address your **browser** can open (`http://localhost:8000`). It is fixed when the frontend image is built, so run `docker compose up --build` after changing it. |
| CORS error in the browser console | `CORS_ORIGINS` in `.env` must contain the exact address you use for the frontend, for example `http://localhost:3000`. |
| Port 3000 or 8000 already in use | Stop the other program, or change the left-hand number in `ports:` in `docker-compose.yml`. |
| `frontend` waits forever | The backend is not healthy yet. Run `docker compose logs backend`. |
| Build fails with `npm ci` errors | `frontend/package-lock.json` must exist. Run `npm install` once in `frontend/` and commit the lock file. |
| Out of memory while building | Give Docker Desktop at least 4 GB RAM (Settings, Resources). |
| Search does not see documents added by the command line | The running server loaded its index at start. Restart it: `docker compose restart backend`. |
