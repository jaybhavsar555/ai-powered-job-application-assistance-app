# Implementation Status

Living status for Career OS. **Phases 0–17 are complete.** See [walkthrough.md](./walkthrough.md) and [deploy.md](./deploy.md).

## Stack (as shipped)

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0 async, Alembic  
- **Frontend**: Next.js App Router, TypeScript, Tailwind, Zustand, React Flow  
- **Workflow**: LangGraph + **durable Postgres checkpointer** (MemorySaver fallback) + Redis Pub/Sub + SSE  
- **LLM**: OpenAI / Ollama / mock — switch live from Canvas (`PUT /llm/provider`)  
- **Scrape**: Playwright (+ httpx/mock) for jobs; site/SERP/mock for company research  
- **Memory**: PostgreSQL WikiEntities + Qdrant vectors  
- **Auth**: Email/password register/login + optional demo JWT  
- **Marketplace**: YAML plugin agents under `app/marketplace/plugins`  
- **Packages**: Tailored resume + cover letter DOCX/PDF under `RESUME_SOURCE_DIR`  
- **CI**: GitHub Actions · **Prod**: `docker-compose.prod.yml`

## Delivery checklist

### Complete (Phases 0–17)

- [x] Workspace shell (nav, inspector, terminal)
- [x] React Flow canvas + SSE telemetry + agent prompt inspector
- [x] OSAgent base + AgentRegistry + PromptRegistry (YAML)
- [x] Job intake, Company Research, ATS, Resume Optimizer, Cover Letter agents
- [x] Approvals UI + Accept/Reject → CoverLetter / ResumeVersion (+ Ready stage)
- [x] Knowledge Vault + job portal seed + semantic search
- [x] Applications Kanban tracker + stage PATCH + Import job
- [x] Analytics summary dashboard
- [x] Local Ollama wiring + embedding pipeline
- [x] Demo auth + **email/password register/login** (`/login`)
- [x] GitHub Actions CI
- [x] Playwright job URL scrape
- [x] Company research gather wired into LangGraph
- [x] **LangGraph checkpoints** (`MemorySaver`, resume SSE, checkpoint API)
- [x] **Agent Marketplace** (YAML plugins + `/marketplace` UI)
- [x] **Production compose** (`docker-compose.prod.yml` + secrets example + [deploy.md](./deploy.md))
- [x] **Phase 16 — Real job-linked workflows**: Canvas job picker + Tracker → Canvas deep link; Approvals use real `job_id`; auto apply-package after both approvals
- [x] **Phase 17 — Durable checkpoints**: `AsyncPostgresSaver` via `CHECKPOINT_BACKEND=postgres` (falls back to MemorySaver); `GET /workflows/checkpointer`

### Optional future ideas

- [ ] OAuth (Google/GitHub)
- [ ] Kubernetes manifests / Helm
- [ ] Paid marketplace / signed plugin packages

### Product layer (not started) — Simple Mode / Career Inbox

The agent workspace (Phases 0–17) is the **Advanced Workspace**. The daily job-seeker product is a **second layer on top** — do not remove Canvas/Vault/Tracker.

Full gap analysis + phased plan: **[product_simple_mode_roadmap.md](./product_simple_mode_roadmap.md)**

- [ ] **Phase 18** — Shell modes + Career Inbox (`/inbox`, `GET /inbox/summary`)
- [ ] **Phase 19** — Jobs page (import + cards; optional auto-Simulate)
- [ ] **Phase 20** — Resume Studio (diff, versions, ATS, download)
- [ ] **Phase 21** — Companies & Recruiters pages (use existing DB stubs)
- [ ] **Phase 22** — Outreach drafts + follow-ups (approve / copy / mark sent)
- [ ] **Phase 23** — Pipeline extensions (recruiter node, richer stages, auto-start)
- [ ] **Phase 24** — OAuth email, extension ingest, deep analytics, vault graph UI

## API surface (implemented)

| Area | Endpoints |
|------|-----------|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST/GET /auth/demo`, `GET /auth/me`, `GET /auth/credentials` |
| Health | `GET /api/v1/health/` |
| LLM | `GET/PUT /llm/provider` (openai \| ollama \| mock) |
| Knowledge | `GET/POST /knowledge/me`, `POST/GET /knowledge/me/search`, `POST /knowledge/me/reindex`, `POST /knowledge/me/seed-job-portals` |
| Jobs | `POST /jobs/ingest`, `GET /jobs/`, `GET /jobs/{id}` |
| Applications | `GET/POST /applications/`, `GET /applications/{id}`, `PATCH /applications/{id}/stage` |
| Approvals | `POST /approvals/decide` |
| Analytics | `GET /analytics/summary` |
| Workflows | `GET /workflows/checkpointer`, `GET /workflows/{job_id}/stream?token=`, `GET /workflows/{job_id}/checkpoint` |
| Resumes | CRUD under `/resumes` |
| Documents | `POST /documents/export/docx`, `GET /documents/resume-library`, `POST /documents/apply-package` |
| Marketplace | `GET /marketplace/plugins`, `POST /marketplace/plugins/{id}/toggle` |

## Local run ports

| Service | Port |
|---------|------|
| Next.js | 3000 |
| FastAPI | **8001** |
| Postgres | 5432 |
| Redis | 6379 |
| Qdrant | 6333 |
| Ollama | 11434 |

See root [README.md](../README.md) and [walkthrough.md](./walkthrough.md) for commands.
