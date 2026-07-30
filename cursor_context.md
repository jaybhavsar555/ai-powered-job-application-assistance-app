# Project Context for Cursor
**Project Name**: AI Powered Job Application Assistance App (Career OS)

Primary continuity file for Cursor. Prefer [docs/walkthrough.md](docs/walkthrough.md), [docs/deploy.md](docs/deploy.md), and [README.md](README.md).

## Product Vision
Platform with AI observability, human-in-the-loop, knowledge graph, and agent visualization. Obsidian/Linear-inspired dark workspace.

## Tech Stack
- **Frontend**: Next.js App Router, Tailwind, Zustand, React Flow, SSE. API base **`http://localhost:8001/api/v1`**.
- **Backend**: FastAPI on **port 8001**, PostgreSQL, Redis Pub/Sub, LangGraph (+ durable Postgres checkpointer), Instructor.
- **LLM**: OpenAI / Ollama / mock via `infrastructure/llm/runtime.py` (Canvas switcher).
- **Memory**: WikiEntity + Qdrant (`infrastructure/memory/`).
- **Auth**: `/auth/register`, `/auth/login`, `/auth/demo` — UI at `/login`.
- **Marketplace**: YAML plugins + `/marketplace`.
- **Packages**: `POST /documents/apply-package` → company folders under `RESUME_SOURCE_DIR`.
- **Checkpoints**: `CHECKPOINT_BACKEND=postgres` → `AsyncPostgresSaver`; falls back to MemorySaver.

## Phases 0–17
- 0–11 — DONE
- **12 — DONE (enhanced)**: Roles + seed accounts on `/login`
  - `admin@example.com` / `Admin123!` (admin)
  - `jay.bhavsar.dev@gmail.com` / `Admin123!` (admin)
  - `demo@example.com` / `Demo1234!` (demo)
  - `user@example.com` / `User1234!` (user)
- **13–15 — DONE**: checkpoints (in-memory), marketplace, prod compose
- **16 — DONE**: Real job-linked workflows (Canvas picker, Tracker deep link, auto package)
- **17 — DONE**: Durable LangGraph checkpoints in Postgres (`GET /workflows/checkpointer`)

## Local services
`docker compose up -d` → Postgres, Redis, Qdrant, Ollama.  
Pull: `qwen2.5:3b`, `nomic-embed-text`.  
API: `uvicorn app.main:app --reload --port 8001`.

## Prod
See [docs/deploy.md](docs/deploy.md).
