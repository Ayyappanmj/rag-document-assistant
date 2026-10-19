# Release checklist

Tick each box only after you have seen it work yourself. The commands show how to check.

## Backend
- [ ] `pytest` passes (from `backend/`)
- [ ] `uvicorn app.main:app --reload` starts and http://localhost:8000/docs loads
- [ ] PDF upload works, and the document reaches **Ready** with correct page and chunk counts
- [ ] Page numbers are preserved (Documents page, View, check a page)
- [ ] Hybrid search works: `POST /api/search` returns `dense_score` and `bm25_score`
- [ ] Ollama answers a question with `[Source: ..., Page N]` citations
- [ ] An unrelated question gets "I couldn't find sufficient evidence"
- [ ] Two PDFs uploaded: a comparison question cites both
- [ ] A made-up claim is flagged (`grounded: false`)

## Frontend
- [ ] `npm run build` succeeds (from `frontend/`)
- [ ] Landing, Dashboard, Documents, Chat, Evaluation and Settings pages load without console errors
- [ ] Chat: sample question, source card opens the passage, Copy, Regenerate, Clear chat, error state (stop Ollama)

## Evaluation
- [ ] `python evaluation/make_sample_pdfs.py` then `python evaluation/evaluate.py --ingest --limit 3` works
- [ ] The Evaluation page shows a "Sample Evaluation" run

## Packaging
- [ ] `docker compose up --build` works and the app opens on http://localhost:3000
- [ ] GitHub Actions run is green
- [ ] `.env` is not in git: `git ls-files | grep -i "\.env"` shows only `.env.example` (and `.env.local.example`)
- [ ] No API keys anywhere: `git grep -n "sk-"` finds nothing

## Deployment
- [ ] Vercel project: Root Directory = `frontend`, `NEXT_PUBLIC_API_URL` set, deploys
- [ ] Backend reachable over HTTPS and `CORS_ORIGINS` contains the Vercel address
- [ ] Upload + chat works from the Vercel address

## Portfolio
- [ ] Screenshots added to `docs/screenshots/`
- [ ] README links and the GitHub URL placeholders replaced (search for `your-username`)
- [ ] LICENSE name replaced (`Your Name`)
- [ ] Resume bullets reviewed; no numbers you did not measure

## Known dependency note
- lucide-react 1.x removed brand icons, so the GitHub icon is a local component (`frontend/components/common/GithubIcon.tsx`). If you upgrade lucide-react and see "export ... was not found", check for renamed icons at https://lucide.dev/icons
