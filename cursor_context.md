# Project Context for Cursor / Antigravity

**Project Name:** AI Powered Job Application Assistance App (**Career OS**)  
**Repo:** https://github.com/jaybhavsar555/ai-powered-job-application-assistance-app  
**Workspace:** `c:\ai_powered_job_application_assistance_app`  
**Status (2026-07-31):** Phases **0–17 complete** (Advanced Workspace). Simple Mode / Career Inbox = **spec only** → [docs/product_simple_mode_roadmap.md](docs/product_simple_mode_roadmap.md) (Phases 18–24).  
**Latest commits on `main`:** durable checkpoints, SSE auth fix, Vault seed without hanging on embeddings.

Use this file to resume work in Antigravity or a new Cursor chat. Prefer also: [docs/user_guide.md](docs/user_guide.md) (how to use features), [docs/implementation_plan.md](docs/implementation_plan.md), [docs/walkthrough.md](docs/walkthrough.md), [docs/deploy.md](docs/deploy.md), [README.md](README.md).

---

## Product vision

Local-first AI OS for job applications: multi-agent LangGraph pipeline, live SSE telemetry, human-in-the-loop approvals, Knowledge Vault + job portals, Kanban tracker, tailored resume/cover packages (DOCX+PDF).

**Primary apply loop**

1. **Vault** — seed/browse job portals  
2. **Tracker** — Import job URL/JD → Wishlist card  
3. **Canvas** — pick that job → Simulate (OpenAI / Ollama / mock)  
4. **Approvals** — approve resume + cover letter  
5. **Package** — auto-write DOCX/PDF under resume folder (or Tracker **Package** button)

---

## Stack & ports

| Layer | Tech |
|-------|------|
| Frontend | Next.js App Router, Tailwind, Zustand, React Flow, SSE |
| Backend | FastAPI, SQLAlchemy async, Alembic, LangGraph, Instructor |
| LLM | OpenAI **or** Ollama — runtime switch `GET/PUT /api/v1/llm/provider` |
| Data | Postgres `5432`, Redis `6379`, Qdrant `6333`, Ollama `11434` |
| API | **`http://localhost:8001/api/v1`** (not 8000) |
| UI | **`http://localhost:3000`** |

**Routes:** `/canvas` · `/vault` · `/tracker` · `/approvals` · `/marketplace` · `/analytics` · `/login`

---

## How to run (Windows)

```bash
# Infra
docker compose up -d
# Ensure Redis publishes 6379: docker compose up -d redis
# Optional local LLM:
docker compose exec ollama ollama pull qwen2.5:3b
docker compose exec ollama ollama pull nomic-embed-text

# Backend (from backend/)
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

# Frontend (from frontend/)
npm run dev
```

**Important:** Kill duplicate listeners on `:8001` if SSE/auth looks flaky (`netstat -ano | findstr :8001`). Only one uvicorn.

**Windows + Postgres checkpointer:** `psycopg` needs SelectorEventLoop — set in `app/main.py` via `ensure_windows_selector_loop_policy()`.

---

## Auth / roles (seeded on API startup)

| Role | Email | Password |
|------|-------|----------|
| admin | `admin@example.com` | `Admin123!` |
| admin | `jay.bhavsar.dev@gmail.com` | `Admin123!` |
| demo | `demo@example.com` | `Demo1234!` |
| user | `user@example.com` | `User1234!` |

- UI: `/login` — register, login, Continue as demo  
- Marketplace plugin toggle: **admin** or **demo** only  
- Frontend may auto-call `POST /auth/demo` — log in as Jay for admin Vault/marketplace  
- **EmailStr** rejects `.local` emails — use `@example.com` (SSE placeholder is `sse@example.com`)

---

## Resume library & packages

- **Source folder:** `C:\Users\Asus\Downloads\resume based on JD`  
- Config: `RESUME_SOURCE_DIR` / `APPLICATION_PACKAGE_DIR` in `backend/.env`  
- Role families: Flutter · Full Stack · AI · SDE (`app/core/target_roles.py` + filename matching)  
- APIs: `GET /documents/resume-library`, `POST /documents/apply-package`  
- Output: `{RESUME_SOURCE_DIR}/{Company}/Jay_Padmakar_Bhavsar_*_{Resume|Cover_Letter}.{docx|pdf}`  
- PDF via **reportlab** (WeasyPrint needs GTK on Windows — not used)

---

## Job portals (Vault seed)

Canonical list: `backend/app/core/job_portals.py`  
Seed: Vault UI **Seed job portals** or `POST /knowledge/me/seed-job-portals`  
Includes: Instahyre, Cutshort, Hirist, Foundit, TopHire, Weekday, YC Jobs, Wellfound, Startup.jobs, We Work Remotely (+ remote-jobs), FlexJobs, Welcome to the Jungle, Hired, Dice.

Seed writes Postgres **without** blocking on embeddings (`index_vectors=False`) so OpenAI 429s don’t hang the button. Semantic search still needs working embeddings + Qdrant (dims must match `EMBEDDING_DIMS`).

---

## LLM dual profile

Env profiles in `backend/.env` (do **not** commit real keys):

- `LLM_PROVIDER=openai|ollama|mock`  
- OpenAI: empty `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL=gpt-4o`  
- Ollama: `OLLAMA_BASE_URL=http://localhost:11434/v1`, `OLLAMA_MODEL=qwen2.5:3b`  
- Runtime: `app/infrastructure/llm/runtime.py` + Canvas **OpenAI | Ollama | Mock** switch  
- If OpenAI quota exceeded → agents fall back to **mocks** (Simulate still completes)

**Security:** An OpenAI key was pasted in chat earlier — **rotate** in OpenAI dashboard; keep only in local `backend/.env` (gitignored).

---

## Phase history (0–17) — all DONE

| Phase | Summary |
|-------|---------|
| 0–9 | Workspace, agents, SSE, vault, tracker, analytics, Qdrant, Ollama, approvals |
| 10 | Playwright/httpx/mock job scrape; Tracker Import job |
| 11 | Company research agent + scrape/SERP/mock |
| 12 | Email/password auth + roles + `/login` + seed accounts |
| 13 | LangGraph checkpoints (MemorySaver) + resume SSE |
| 14 | Agent Marketplace (YAML plugins, Skill Gap Coach) |
| 15 | `docker-compose.prod.yml` + `.env.production.example` + deploy docs |
| 16 | Real job-linked workflows: Canvas job picker, Tracker→Canvas, auto package after approvals |
| 17 | Durable `AsyncPostgresSaver` (`CHECKPOINT_BACKEND=postgres`) + `GET /workflows/checkpointer` |

Extras in same era: LLM provider switch, apply-package DOCX/PDF, Vault portal seed UX, agent Inspector prompt edit.

---

## Optional backlog (not formal phases)

- [ ] OAuth (Google/GitHub)  
- [ ] Kubernetes / Helm  
- [ ] Paid / signed marketplace plugin packages  
- [ ] Stronger E2E Playwright coverage beyond smoke  
- [ ] Reindex Vault vectors after embedding model/dim changes  

---

## Key code map

| Area | Path |
|------|------|
| LangGraph | `backend/app/workflows/graph.py` |
| Checkpoints | `backend/app/infrastructure/checkpoints.py` |
| Workflow SSE | `backend/app/application/services/workflow.py`, `endpoints/workflows.py` |
| LLM client/runtime | `backend/app/infrastructure/llm/` |
| Apply package | `backend/app/application/services/apply_package.py` |
| Resume scan | `backend/app/infrastructure/resume_library.py` |
| Job portals | `backend/app/core/job_portals.py` |
| Auth seed | `backend/app/application/services/auth_seed.py` |
| Marketplace | `backend/app/marketplace/` |
| Canvas UI | `frontend/src/app/(workspace)/canvas/page.tsx` |
| Job picker / LLM switch | `frontend/src/components/workflow/` |
| Tracker | `frontend/src/components/tracker/` |
| Approvals + auto package | `frontend/src/app/(workspace)/approvals/page.tsx` |

---

## Bugs fixed recently (don’t regress)

1. **SSE 401** — `User(email="…@career-os.local")` failed EmailStr; use `sse@example.com` in `workflows._user_from_token`.  
2. **Ghost uvicorn on 8001** — multiple PIDs → stale code; kill all then restart one.  
3. **Redis not reachable** — ensure compose publishes `6379:6379` (`docker compose up -d redis`). Event bus has in-process fallback.  
4. **Vault seed hang** — embedding OpenAI 429 retries; portal seed skips vectors.  
5. **Canvas demo job** — prefer real Tracker `job_id`; demo UUID is mock-only.

---

## Suggested next work (if continuing in Antigravity)

1. Switch Canvas LLM to **Ollama** or **Mock** if OpenAI quota is exhausted.  
2. End-to-end: Import real posting → Canvas Simulate → Approvals → confirm package folder.  
3. Optional Phase 18+: OAuth, or Helm, or polish Skill Gap Coach into Canvas after enable.  
4. Keep `cursor_context.md` + `docs/implementation_plan.md` in sync when adding phases.

---

## Agent transcript (this continuity thread)

Prior Cursor chat: job portals, resume folder packages, OpenAI/Ollama switch, Jay admin, Phase 16–17, SSE fix, Vault seed.  
Transcript folder (Cursor): `C:\Users\Asus\.cursor\projects\c-ai-powered-job-application-assistance-app\agent-transcripts\`  
Cite prior chats as `[title](uuid excluding .jsonl)` if needed.

**Do not commit** `backend/.env`. Push only after tests; current `main` is on GitHub.
