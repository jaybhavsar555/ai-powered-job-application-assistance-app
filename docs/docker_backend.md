# Local Docker backend (no venv)

Career OS keeps **Python deps inside the API image**. You do **not** need `backend/venv` on disk.

## What runs where

| Piece | Where | Notes |
|-------|--------|------|
| Postgres, Redis, Qdrant, Ollama, **API** | Docker Compose | Packages installed in image |
| Next.js frontend | Host (`npm run dev`) | Light; only Node modules locally |
| Resume files | Host folder bind-mounted | `C:\Users\Asus\Downloads\resume based on JD` → `/data/resumes` |

## Daily start

```powershell
cd c:\ai_powered_job_application_assistance_app

# Infra + API (rebuild when requirements.txt / Dockerfile change)
docker compose up -d --build api

# Frontend only on the host
cd frontend
npm run dev
```

API: http://localhost:8001/docs · UI: http://localhost:3000

## Important Docker env overrides

`backend/.env` may say `localhost` for DB/Ollama — that is for a **host** uvicorn.  
Compose **overrides** those for the `api` container:

- `DATABASE_URL=...@db:5432/...`
- `REDIS_URL=redis://redis:6379/0`
- `QDRANT_URL=http://qdrant:6333`
- `OLLAMA_BASE_URL=http://ollama:11434/v1`
- `RESUME_SOURCE_DIR=/data/resumes`

## Space tip

Python deps live in the image (no host `venv`). The API image is large **on purpose**:

| Included in image | Why |
|-------------------|-----|
| **TeXLive + `pdflatex`** | ATS-friendly LaTeX resume PDFs |
| **Playwright Chromium** | Real JS job-page scrape (`POST /jobs/ingest`) — not httpx/mock fallback |

No host `playwright install` or TeX install required.

```powershell
# Optional: remove an old local venv if it still exists
Remove-Item -Recurse -Force .\backend\venv -ErrorAction SilentlyContinue
```

First build (TeX + Chromium) can take several minutes and grow the image by a few GB.

## Rebuild when deps change

```powershell
docker compose build --no-cache api
docker compose up -d api
```

## Logs / shell

```powershell
docker compose logs -f api
docker compose exec api bash
```
