# AI Powered Job Application Assistant (Career OS)

A local-first **AI Operating System** for job applications: multi-agent LangGraph pipelines, real-time telemetry, human-in-the-loop approvals, a Knowledge Vault with semantic search, and a Kanban application tracker.

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js (App Router), Tailwind, Zustand, React Flow, SSE |
| Backend | FastAPI, SQLAlchemy async, Alembic, LangGraph, Instructor |
| LLM | **Ollama** (default, OpenAI-compatible) or OpenAI cloud |
| Data | PostgreSQL, Redis (Pub/Sub), Qdrant (vectors) |
| Infra | Docker Compose, GitHub Actions CI |

## Workspace routes

| Route | Purpose |
|-------|---------|
| `/canvas` | Agent pipeline + job picker · Simulate against a Tracker job · LLM switch · durable checkpoints |
| `/vault` | Knowledge Graph entities + Qdrant semantic search |
| `/approvals` | Approve resume/cover letter · auto-writes DOCX/PDF package |
| `/tracker` | Kanban · Import job · **Canvas** deep link · Package |
| `/marketplace` | Enable/disable optional agent plugins |
| `/login` | Register / sign in / demo |

## Quick Start

### 1. Infrastructure + local LLM
```bash
docker compose up -d
docker compose exec ollama ollama pull qwen2.5:3b
docker compose exec ollama ollama pull nomic-embed-text
```

Services: Postgres `5432`, Redis `6379`, Qdrant `6333`, Ollama `11434`.

### 2. Environment
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Defaults use **local Ollama** (`OPENAI_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=qwen2.5:3b`).
If the chat model isn’t pulled yet, agents fall back to deterministic mocks so Simulate still completes.  
For OpenAI cloud: clear `OPENAI_BASE_URL`, set `OPENAI_API_KEY`, `LLM_MODEL=gpt-4o`.

Frontend API URL defaults to **`http://localhost:8001/api/v1`** (port **8001** avoids clashes with other apps on 8000).

### 3. Backend
```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium   # optional; httpx/mock scrape still work
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```
Docs: http://localhost:8001/docs

### 4. Frontend
```bash
cd frontend
npm install
npm run dev
```
UI: http://localhost:3000/canvas  

On first load the app calls `POST /api/v1/auth/demo` and stores a JWT so Vault / Tracker / Analytics work without a full login UI.

## Agent pipeline

1. **Job Intake** — normalize JD → structured JSON  
2. **Company Research** — site/SERP gather → structured hooks (funding, stack, culture)  
3. **ATS Analyzer** — score + missing keywords  
4. **Resume Optimizer** — weave keywords into bullets  
5. **Cover Letter** — personalized letter + research hooks 

All agents inherit `OSAgent` (telemetry → Postgres `agent_event_logs` + Redis `workflow_events` → SSE → React Flow / Inspector).

LLM calls go through `app/infrastructure/llm/client.py` (shared OpenAI-compatible client + Instructor).

## Key APIs

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/v1/auth/demo` | Dev JWT |
| GET/POST | `/api/v1/knowledge/me` | Wiki entities; create indexes Qdrant |
| POST/GET | `/api/v1/knowledge/me/search` | Semantic search |
| POST | `/api/v1/knowledge/me/reindex` | Re-embed all entities |
| GET/POST | `/api/v1/applications/` | Tracker board |
| PATCH | `/api/v1/applications/{id}/stage` | Kanban move |
| GET | `/api/v1/analytics/summary` | Telemetry aggregates |
| GET | `/api/v1/workflows/{job_id}/stream` | SSE workflow stream |
| POST | `/api/v1/jobs/ingest` | URL scrape (Playwright) or raw text → Wishlist |

## CI/CD

`.github/workflows/ci.yml` on `main`: frontend lint/build, backend import + pytest, Docker backend image.

## Repo layout

- `backend/` — FastAPI, agents, workflows, memory (Qdrant/embeddings)
- `frontend/` — Career OS workspace UI
- `docs/` — Architecture & status docs
- `cursor_context.md` — Cursor session continuity file
- `docker-compose.yml` — Postgres, Redis, Qdrant, Ollama

## More documentation

- [Current system walkthrough](docs/walkthrough.md) — phases 0–11, verify steps, **troubleshooting** (model 404, SSE)
- [Architecture overview](docs/architecture_design.md)
- [Implementation status](docs/implementation_plan.md)
- [Architecture deep-dives](docs/architecture/)
- [Production deploy](docs/deploy.md) — compose prod + secrets
- [Cursor continuity](cursor_context.md)
