# Local Docker backend (no host Python venv)

Career OS runs the **API and all Python dependencies inside Docker**.  
You do **not** need `backend/venv`, host `pip install`, Playwright, or TeX on your laptop.

Frontend stays on the host: `cd frontend && npm install && npm run dev`.

Full cross-OS setup (Windows / macOS / Linux) lives in the root [README.md](../README.md).

## What runs where

| Piece | Where | Notes |
|-------|--------|------|
| Postgres, Redis, Qdrant, Ollama, **API** | Docker Compose | Packages installed in the `api` image |
| Next.js frontend | Host (`npm run dev`) | Only Node modules locally |
| Base resumes | Host `./data/resumes` → container `/data/resumes` | Put PDF/DOCX/MD here |
| Apply packages | Host `./data/packages` → `/data/packages` | Written after Approvals |

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or [Docker Engine + Compose](https://docs.docker.com/engine/install/) (Linux)
- Node.js 20+ for the frontend only

## Daily start

```bash
# From repo root — backend stack (always Docker)
docker compose up -d

# Frontend on the host
cd frontend
npm install   # first time / after package.json changes
npm run dev
```

- API docs: http://localhost:8001/docs  
- UI: http://localhost:3000 (or `npm run dev -- -p 3001`)

### First-time model pull

```bash
docker compose exec ollama ollama pull qwen2.5:3b
```

Mock LLM is **off** by default (`LLM_ALLOW_MOCK=false`). Without a pulled model, agents fail visibly instead of inventing content.

### Optional NVIDIA GPU

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

Requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html). Skip on macOS / CPU-only machines.

## Important Docker env overrides

`backend/.env` may say `localhost` for DB/Ollama — that is for a rare **host** uvicorn.  
Compose **overrides** those for the `api` container:

- `DATABASE_URL=...@db:5432/...`
- `REDIS_URL=redis://redis:6379/0`
- `QDRANT_URL=http://qdrant:6333`
- `OLLAMA_BASE_URL=http://ollama:11434/v1`
- `LLM_PROVIDER=ollama`
- `RESUME_SOURCE_DIR=/data/resumes`
- `APPLICATION_PACKAGE_DIR=/data/packages`

## What’s inside the API image

| Included | Why |
|----------|-----|
| Python deps from `requirements.txt` | No host venv |
| **TeXLive + `pdflatex`** | ATS-friendly LaTeX resume PDFs |
| **Playwright Chromium** | Real JS job-page scrape |

First `docker compose up -d --build` can take several minutes and produce a multi‑GB image — that is expected.

## Rebuild when deps change

```bash
docker compose build --no-cache api
docker compose up -d api
```

## Logs / shell

```bash
docker compose logs -f api
docker compose exec api bash
docker compose exec api python -m pytest -q
```

## Do not

- Do not document “run uvicorn on the host” as the default path
- Do not commit real `backend/.env` secrets
- Do not enable `LLM_ALLOW_MOCK` for daily use (hides missing models / credits)
