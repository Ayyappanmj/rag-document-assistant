# Deployment guide

```
USER  ->  VERCEL (Next.js frontend)  --HTTPS-->  BACKEND (FastAPI + FAISS + BM25 + SQLite)  ->  LLM
```

Vercel hosts only the frontend. **Never try to run Ollama, FAISS or the embedding model inside Vercel serverless
functions**: they need a long-running process, local disk and gigabytes of memory.

> **Read this first: there is no login yet.** Anyone who knows your backend URL can upload or delete documents and
> spend your LLM quota. Until authentication is added, keep the URL private, use a throwaway LLM key with low
> limits, and do not put real confidential documents on a public server.

## 1. Free-tier reality check

Free tiers change often. These notes were checked against the providers' own pages in October 2026. Re-check the
links before you rely on them.

| Option | Free? | Fits this backend? | Why |
|---|---|---|---|
| **Vercel Hobby** (frontend) | Yes, for personal non-commercial use | Yes | [Fair use](https://vercel.com/docs/limits/fair-use-guidelines): Hobby is restricted to non-commercial personal use |
| **Render free web service** | Yes | **No** | [512 MB RAM, 0.1 CPU](https://render.com/docs/compute-plans), filesystem is ephemeral (uploads, SQLite and the FAISS index are lost on every restart or spin-down), [spins down after 15 minutes idle](https://render.com/docs/free) and takes about a minute to wake. PyTorch plus the embedding model will most likely not fit in 512 MB (my estimate, not tested) |
| **Hugging Face Spaces (Docker)** | No | No | [Docker and Gradio Spaces now require a paid plan to create](https://huggingface.co/docs/hub/en/spaces-overview); only Static Spaces are free |
| **Oracle Cloud Always Free (Ampere A1)** | Yes (card needed for identity check) | **Yes, best free option** | [Up to 4 OCPU, 24 GB RAM, 200 GB storage](https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm), persistent disk, runs `docker compose`. Downsides: "out of capacity" errors are common in popular regions, and idle instances can be reclaimed |
| **Your own computer + free tunnel** | Yes | Yes, for demos | Backend runs on your machine, a tunnel gives it an HTTPS address. Only works while your computer is on |

**LLM without a GPU:** Ollama on CPU works but is slow. A free alternative is an OpenAI-compatible hosted API.
For example Groq has a free tier, base URL `https://api.groq.com/openai/v1` (rate limits apply, check the Groq
console). Set `LLM_PROVIDER=openai`, `OPENAI_BASE_URL`, `OPENAI_API_KEY` and `OPENAI_MODEL` in the backend `.env`.
The key stays on the backend and is never sent to the browser.

## 2. Frontend on Vercel

1. Push the project to GitHub (never commit `.env` files; `.gitignore` already excludes them).
2. In Vercel: **Add New, Project**, import the repository.
3. Set **Root Directory** to `frontend`. Framework preset: Next.js (detected automatically).
4. Add environment variables:
   - `NEXT_PUBLIC_API_URL` = your backend's **HTTPS** address, for example `https://api-yourname.duckdns.org`
   - `NEXT_PUBLIC_GITHUB_URL` = your repository URL
5. Deploy. Values starting with `NEXT_PUBLIC_` are baked in at build time, so **redeploy after changing them**.
6. Add your Vercel address to the backend: `CORS_ORIGINS=https://your-app.vercel.app` (comma-separated for
   several), then restart the backend.

Two things that commonly go wrong:
- **Mixed content:** a page served over HTTPS cannot call an `http://` backend. The backend needs HTTPS.
- **Preview deployments** get different addresses. CORS only allows the origins you list.

## 3. Backend, option A: Oracle Cloud Always Free VM (persistent)

1. Create an Oracle Cloud account, then **Compute, Instances, Create instance**. Choose an Ubuntu image
   (aarch64), shape **VM.Standard.A1.Flex** (for example 2 OCPU and 12 GB, or the full 4 and 24), add your SSH key,
   and keep the public IP.
2. In the instance's network security list, allow inbound TCP **80** and **443** (and 22 for SSH).
3. SSH in and install Docker:

       curl -fsSL https://get.docker.com | sudo sh
       sudo usermod -aG docker $USER      # then log out and back in

4. Ubuntu images on Oracle block ports at the OS level too. A common fix (check the rule number first with
   `sudo iptables -L INPUT --line-numbers`):

       sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
       sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
       sudo apt-get install -y iptables-persistent && sudo netfilter-persistent save

5. Get an HTTPS-capable hostname for the VM's IP: a free dynamic-DNS subdomain (for example DuckDNS) or your own
   domain. Point it at the VM's public IP.
6. Get the code and configure it:

       git clone https://github.com/your-username/rag-document-assistant.git
       cd rag-document-assistant
       cp .env.example .env
       nano .env

   Set at least:

       API_DOMAIN=api-yourname.duckdns.org
       BACKEND_BIND=127.0.0.1
       CORS_ORIGINS=https://your-app.vercel.app
       SECRET_KEY=<output of: openssl rand -hex 32>
       LLM_PROVIDER=openai
       OPENAI_BASE_URL=https://api.groq.com/openai/v1
       OPENAI_API_KEY=<your key>
       OPENAI_MODEL=<a model your provider offers>

7. Start the backend and the HTTPS proxy (Caddy fetches the certificate automatically):

       docker compose -f docker-compose.yml -f deploy/docker-compose.prod.yml up -d --build backend caddy
       curl https://api-yourname.duckdns.org/api/health

8. Put that address into Vercel as `NEXT_PUBLIC_API_URL` and redeploy the frontend.

Using local Ollama on the VM instead of a hosted API: add `--profile ollama` to the command, set
`DOCKER_OLLAMA_URL=http://ollama:11434`, then `docker compose exec ollama ollama pull llama3.2`. On CPU this is slow.

These deployment files (`deploy/Caddyfile`, `deploy/docker-compose.prod.yml`) have not been run against a live
server by the author of this guide. If something fails, `docker compose logs caddy backend` shows why.

## 4. Backend, option B: your computer + a tunnel (demos)

    docker compose up -d backend
    cloudflared tunnel --url http://localhost:8000     # prints an https://....trycloudflare.com address

Use that address as `NEXT_PUBLIC_API_URL` in Vercel (redeploy) and add your Vercel address to `CORS_ORIGINS`
(restart the backend). Quick tunnels get a new address each time they start, and the demo only works while your
computer is on. Check Cloudflare's current documentation for how quick tunnels behave.

## 5. Free-tier limitations and what they mean for this app

| Limitation | Effect here | What to do |
|---|---|---|
| **Ephemeral filesystem** (Render free, Hugging Face free storage) | Uploads, the SQLite database and the FAISS index disappear on restart | Use a host with a persistent disk (Option A), or accept re-uploading a few demo PDFs |
| **FAISS lives on disk and in RAM** | A fresh container has an empty index; running several workers would give each its own copy | One worker (already the default). Back up the data volume (below) |
| **Model storage** | The embedding model (about 90 MB) is downloaded again if the cache is lost | The backend image downloads it at build time |
| **CPU and RAM** | 512 MB hosts cannot load PyTorch plus the model; free CPUs make local LLMs slow | Use at least 2 GB RAM for the backend, and a hosted LLM API |
| **Request timeouts** | A slow CPU LLM can exceed a platform's request limit | Use a smaller or hosted model; `LLM_TIMEOUT_SECONDS` controls the backend's own limit |
| **Cold starts** | A spun-down service takes about a minute to wake and the first request is slow | Warm it before a demo or interview |

If no free host can keep the data, the usual redesign is a managed vector database, a hosted embedding API and a
hosted LLM, with the FastAPI app staying stateless. This project does not implement that variant.

## 6. Backups (Option A)

    docker run --rm -v rag-document-assistant_rag_data:/data -v "$PWD":/backup alpine \
        tar czf /backup/rag_data.tgz -C /data .

## 7. Before you share the link

- No authentication exists. Share the URL only with people you trust.
- `SECRET_KEY` is set to a random value in `.env`, and `.env` is not committed.
- `docker compose logs backend` shows no errors and `/api/health` returns `ok`.
- CORS lists only your real frontend address.
