# Current System Walkthrough

Status document for what is **actually built** in Career OS (**Phases 0–11 complete**). Prefer this over older phase notes that used different numbering.

## Runtime topology

```text
Browser (Next.js :3000)
    │  JWT from POST /auth/demo
    ▼
FastAPI (:8001) ──► PostgreSQL
    │            ──► Redis Pub/Sub (workflow_events) + in-process fan-out
    │            ──► Qdrant (wiki_entities vectors)
    │            ──► Playwright / httpx (job + company page scrape)
    └────────────► Ollama (:11434)  chat + embeddings
```

**Port note:** API uses **8001** because host `:8000` is often taken by other Docker services.

## Frontend workspace

| Route | Status | Behavior |
|-------|--------|----------|
| `/canvas` | Live | Simulate → SSE → React Flow node pulse + Inspector + Terminal |
| `/vault` | Live | List/create WikiEntities; semantic search via Qdrant |
| `/approvals` | Live | Accept/Reject → persists CoverLetter / ResumeVersion, stage → Ready |
| `/tracker` | Live | **Import job** (URL/text) + Kanban; drag → `PATCH .../stage` |
| `/analytics` | Live | Summary from `AgentEventLog` + pipeline counts |

Auth bootstrap: `Providers` → `ensureDemoAuth()` → axios / SSE `?token=` (EventSource cannot send Authorization headers).

## Agent pipeline (LangGraph)

1. **job_intake_agent** — normalize JD (from DB job if `job_id` exists, else demo text)  
2. **company_research_agent** — site / DuckDuckGo HTML / mock → structured hooks  
3. **ats_analyzer** — score + missing skills  
4. **resume_optimizer** — weave missing keywords into bullets  
5. **cover_letter_agent** — letter using resume + research hooks → human approval  

All inherit `OSAgent` → Postgres `agent_event_logs` + Redis/local `workflow_events` → SSE.

If the chat model is missing or Ollama errors, `structured_generate(...)` **falls back to mocks** so Simulate still completes.

## Backend modules (high signal)

| Area | Path | Role |
|------|------|------|
| Shared LLM | `infrastructure/llm/client.py` | OpenAI SDK + Instructor; Ollama or cloud; mock fallback |
| Job scrape | `infrastructure/scraping/job_page.py` | Playwright → httpx → mock |
| Company signals | `infrastructure/scraping/company_research.py` | Site / SERP / mock |
| Embeddings | `infrastructure/memory/embeddings.py` | `nomic-embed-text` or hash fallback |
| Vector store | `infrastructure/memory/vector_store.py` | Qdrant collection `wiki_entities` |
| OSAgent | `application/agents/base.py` | Latency/tokens, Postgres log, events |
| Agents | `application/agents/*.py` | Intake, Research, ATS, Resume, Cover Letter |
| Graph | `workflows/graph.py` | LangGraph pipeline |
| Event bus | `infrastructure/events/bus.py` | Redis + in-process queues |
| Approvals | `services/approval.py` | Persist artifacts + Ready stage |
| Applications | `services/application.py` | Tracker CRUD / stage |
| Jobs | `services/job.py` | Ingest + scrape + Wishlist application |
| Analytics | `services/analytics.py` | Telemetry aggregates |
| Knowledge | `services/knowledge.py` | Wiki CRUD + search + reindex |

## Data model (current)

- **`wiki_entities`** — graph nodes (`entity_type`, `title`, `content` JSONB, `vector_id`)
- **`applications`** — stages: Wishlist → Researching → Ready → Applied → Interview → Rejected  
- **`agent_event_logs`** — tokens, latency, `action_type` (`execution` \| `error`), evidence  
- **`jobs`**, **`resumes`**, **`resume_versions`**, **`cover_letters`**, **`companies`**, etc.

Job ingest **auto-creates** a Wishlist `application`. Approvals can advance to **Ready**.

## LLM configuration

| Env | Local default | Cloud alternative |
|-----|---------------|-------------------|
| `OPENAI_BASE_URL` | `http://localhost:11434/v1` | empty |
| `OPENAI_API_KEY` | `ollama` | `sk-…` |
| `LLM_MODEL` | **`qwen2.5:3b`** | `gpt-4o` |
| `EMBEDDING_MODEL` | `nomic-embed-text` | `text-embedding-3-small` |
| `EMBEDDING_DIMS` | `768` | `1536` |

```bash
docker compose exec ollama ollama pull qwen2.5:3b
docker compose exec ollama ollama pull nomic-embed-text
# Optional stronger chat model:
# docker compose exec ollama ollama pull qwen2.5:7b
# then set LLM_MODEL=qwen2.5:7b in backend/.env and restart uvicorn
```

## Phase history (Career OS numbering)

| Phase | Outcome |
|-------|---------|
| 0–1 | Workspace layout + routes |
| 2 | UI components (ApprovalCard, Telemetry, Custom nodes) |
| 3 | WikiEntity + AgentEventLog schema |
| 4 | AgentRegistry + OSAgent + PromptRegistry |
| 5–6 | Redis bus + SSE + live Canvas / Inspector / Terminal |
| 7 | Approvals + Vault UI |
| 8 | Tracker Kanban + Analytics + Qdrant long-term memory |
| 9 | Approval Accept/Reject → DB + Ready stage; demo auth; SSE `?token=` |
| 10 | Playwright job URL scrape + Tracker **Import job** |
| 11 | `company_research_agent` (site/SERP/mock → cover-letter hooks) |

### Still deferred (not numbered)

- Full email/auth product login  
- LangGraph checkpoints per application  
- Agent Marketplace  
- Production deploy / secrets  

## Troubleshooting

### `model 'qwen2.5:7b' not found` (or any model 404)

1. Confirm what the API is configured to use: `LLM_MODEL` in `backend/.env` (default **`qwen2.5:3b`**).  
2. List local models: `docker compose exec ollama ollama list`  
3. Pull the configured model: `docker compose exec ollama ollama pull qwen2.5:3b`  
4. **Restart uvicorn** after changing `.env` (`get_settings` is cached).  
5. If the model is still missing, agents should fall back to mocks — if you still see a hard `AGENT_ERROR`, the API process is stale; restart it.

### SSE connection failed

- API must be on **:8001** (`NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1`).  
- Redis should be up (`docker compose up -d`); bus also has an in-process fallback.  
- Demo JWT must exist (wait for auth bootstrap, then Simulate again).

## How to verify quickly

```bash
docker compose up -d
docker compose exec ollama ollama pull qwen2.5:3b
docker compose exec ollama ollama pull nomic-embed-text

cd backend
# optional for richer scrapes:
# playwright install chromium
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001

cd frontend && npm run dev
```

1. Open `/tracker` → Import job (URL or paste) → Wishlist card appears.  
2. Open `/canvas` → Simulate → Terminal shows all five agents → Approvals.  
3. Open `/vault` → add entity → Semantic Search (needs `nomic-embed-text`).  
4. Open `/analytics` → see runs / success rates.
