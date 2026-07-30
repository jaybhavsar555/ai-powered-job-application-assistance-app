# Career OS — User Guide

How to use every workspace feature with real jobs (not the Canvas demo UUID).  
UI: **http://localhost:3000** · API: **http://localhost:8001**

---

## Before you start

1. Infra: `docker compose up -d` (Postgres, Redis, Qdrant, Ollama)
2. Backend: `uvicorn app.main:app --reload --host 127.0.0.1 --port 8001` from `backend/`
3. Frontend: `npm run dev` from `frontend/`
4. Open **http://localhost:3000/login** and sign in

| Account | Email | Password | Notes |
|---------|-------|----------|-------|
| You (admin) | `jay.bhavsar.dev@gmail.com` | `Admin123!` | Preferred for full testing |
| Demo | `demo@example.com` | `Demo1234!` | Marketplace toggle allowed |
| Admin | `admin@example.com` | `Admin123!` | Seeded admin |
| User | `user@example.com` | `User1234!` | Standard role |

**Continue as demo** also works, but each browser/session has its own JWT — jobs you import belong to that user.

---

## The real apply loop (recommended)

```text
Vault (portals) → Tracker (import real JD) → Canvas (pick that job + Simulate)
    → Approvals (accept resume + cover) → Package (DOCX/PDF on disk)
```

Do **not** rely on the Canvas placeholder job id `00000000-…` for packaging or approvals. Always pick a **Tracker card**.

---

## 1. Login (`/login`)

**Use when:** first visit, or after clearing storage.

- **Register** — new email + password  
- **Sign in** — existing account  
- **Continue as demo** — quick JWT (good for demos; prefer Jay for your real tracker)

After login you land in the workspace sidebar: Canvas, Vault, Tracker, Approvals, Marketplace, Analytics.

---

## 2. Knowledge Vault (`/vault`)

**Use when:** you want a reusable library of portals, notes, and searchable knowledge.

| Action | What it does |
|--------|----------------|
| **Seed job portals** | Adds Instahyre, Cutshort, Wellfound, YC Jobs, etc. as `job_portal` entities |
| **Create entity** | Manual wiki node (title, type, content JSON) |
| **Semantic search** | Qdrant vector search (needs working embeddings) |
| **Reindex** | Re-embeds all entities |

**Use cases**

- Keep a personal list of boards you apply on  
- Store company notes / interview prep as entities  
- Search “Flutter remote India” once portals + notes are indexed  

Open a portal URL from Vault → copy a posting → import it in Tracker.

---

## 3. Jobs Tracker (`/tracker`) — real jobs live here

**Use when:** you want a Kanban of applications you actually care about.

### Import a real job

Use **Import job** at the top:

**Option A — URL scrape**

1. Paste a posting URL (Greenhouse, Lever, company careers page, etc.)
2. Click **Ingest**
3. Playwright (or httpx) scrapes the page; if scrape fails you still get a card (check Advanced and paste the JD)

**Option B — Paste JD text (most reliable)**

1. Click **More options**
2. Fill **Role title**, **Company**, paste the full **job description**
3. Optionally still add the **URL** for reference
4. Click **Ingest**

The job is saved and a Kanban card appears in **Wishlist**.

### Kanban stages

Drag cards across:

`Wishlist` → `Researching` → `Ready` → `Applied` → `Interview` → `Rejected`

Approving both resume + cover letter can move the app toward **Ready**.

### Card actions

| Button | Purpose |
|--------|---------|
| **Canvas** | Opens `/canvas?job_id=…` with that real job selected |
| **Package** | Writes tailored resume + cover letter DOCX/PDF under your resume folder |

---

## 4. Agent Canvas (`/canvas`)

**Use when:** you want the multi-agent pipeline to run against a **real** tracker job.

### Setup

1. Open Tracker → click **Canvas** on a card, **or** pick the job in the Canvas job picker  
2. Choose LLM: **OpenAI** (fast, needs quota) · **Ollama** (local; click once to warm) · **Mock** (instant demo)  
3. Click **Simulate** / start workflow  

### What each agent does

| Agent | Output |
|-------|--------|
| Job Intake | Structured JD (skills, years, responsibilities) |
| Company Research | Summary, stack, cover-letter hooks (runs in parallel with ATS) |
| ATS Analyzer | Score + missing keywords |
| Resume Optimizer | Tailored summary + bullets |
| Cover Letter | Personalized letter using research hooks |

Watch React Flow nodes, Inspector evidence, and the timeline. Status shows **durable** checkpoints when Postgres checkpointer is on (`CHECKPOINT_BACKEND=postgres`).

### Resume after interrupt

If the run pauses or the API restarts mid-run, use **Resume** — LangGraph thread id is the `job_id`.

---

## 5. Approvals (`/approvals`)

**Use when:** humans must sign off before treating documents as ready.

1. After Canvas finishes, open Approvals (or follow the in-app link)  
2. Review resume version + cover letter for that run  
3. **Approve** both  

On dual approve, Career OS can auto-write the apply package (DOCX + PDF) for that company.

Reject to keep iterating (re-run Canvas or edit prompts in Inspector when configurable).

---

## 6. Apply packages (disk)

**Config** (`backend/.env`):

- `RESUME_SOURCE_DIR` — your templates folder (e.g. `C:\Users\Asus\Downloads\resume based on JD`)
- `APPLICATION_PACKAGE_DIR` — optional override for output; empty = write under `RESUME_SOURCE_DIR`

**Output pattern**

```text
{RESUME_SOURCE_DIR}/{Company}/
  Jay_Padmakar_Bhavsar_*_Resume.docx|pdf
  Jay_Padmakar_Bhavsar_*_Cover_Letter.docx|pdf
```

Role family (Flutter / Full Stack / AI / SDE) is inferred from the JD + your library filenames.

**Use cases**

- Generate a company-specific folder before applying on Instahyre / Greenhouse  
- Re-run **Package** from Tracker after tweaking approvals  

---

## 7. Marketplace (`/marketplace`)

**Use when:** you want optional agent plugins (admin/demo only).

- Toggle plugins on/off  
- Enabled plugins can extend the pipeline (e.g. skill-gap style agents)

Standard `user@example.com` can view but not toggle.

---

## 8. Analytics (`/analytics`)

**Use when:** you want telemetry on agent runs (latency, success/error counts).

Fed from `agent_event_logs` after Canvas simulations. Empty until you run real workflows.

---

## 9. LLM provider switch

On Canvas:

| Mode | Best for |
|------|----------|
| **OpenAI** | Quality + speed (needs billing/quota) |
| **Ollama** | Offline / free; first click **warms** the model — wait ~10s then Simulate |
| **Mock** | UI demos when you don’t care about LLM text |

OLLAMA tip: use `qwen2.5:3b` on a 4GB GPU (GTX 1650 Ti). Docker Compose enables `gpus: all` — confirm with `docker exec … nvidia-smi` and `size_vram > 0` on `/api/ps`. Prefer Ollama over OpenAI when cloud quota is exhausted.

---

## End-to-end use cases

### A. Apply to a Greenhouse role this week

1. Login as Jay  
2. Vault → Seed job portals (once)  
3. Open Wellfound / Greenhouse → copy posting URL + JD  
4. Tracker → Import (URL + paste JD in More options)  
5. Card → **Canvas** → Ollama or OpenAI → Simulate  
6. Approvals → approve resume + cover  
7. Confirm company folder under `RESUME_SOURCE_DIR`  
8. Drag card to **Applied** after you submit on the board  

### B. Tailor for Flutter vs AI roles

1. Keep both resume templates in `RESUME_SOURCE_DIR` with clear filenames  
2. Import a Flutter JD vs an AI JD  
3. Run Canvas + Package — library matcher picks the closest template family  

### C. Interview prep from Vault

1. Create entities: `company_note`, `interview_question`  
2. Use semantic search before calls  
3. Keep Tracker stage at **Interview**  

### D. Demo for a friend (no API keys)

1. Continue as demo  
2. Canvas → **Mock** → Simulate  
3. Show Tracker/Approvals UI without waiting on LLM  

### E. Durable run across API restart

1. Import real job → Canvas Simulate  
2. Restart uvicorn mid-pipeline (optional stress test)  
3. Resume with same `job_id` — Postgres checkpointer restores thread  

---

## What is “demo / mock” vs “real”

| Thing | Real? | Notes |
|-------|-------|-------|
| Tracker card from Import | **Yes** | Stored in Postgres for your user |
| Canvas job `00000000-…` | No | Placeholder when no job selected |
| LLM **Mock** provider | No | Deterministic agent text |
| Scrape fallback text | Partial | Card exists; paste JD for full fidelity |
| Approvals + Package | **Yes** | Needs a real application / job_id |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Tracker empty after ingest | Wrong user JWT — login as the same account |
| Canvas ignores my job | Use Tracker **Canvas** button or picker; confirm `?job_id=` |
| Ollama very slow | Click Ollama once to warm; don’t use 7b on CPU for demos |
| OpenAI fails / falls back to mock | Quota 429 — switch Ollama or Mock |
| Package missing | Approve both docs; check `RESUME_SOURCE_DIR` exists |
| SSE / Simulate stuck | Only one process on `:8001`; refresh token via login |
| Scrape returns thin text | **More options** → paste full JD |

API docs (interactive): http://localhost:8001/docs  

---

## Related docs

- [README](../README.md) — install & stack  
- [Walkthrough](walkthrough.md) — engineering status  
- [Simple Mode roadmap](product_simple_mode_roadmap.md) — Career Inbox & product layer (not built yet)  
- [Deploy](deploy.md) — production compose  
- [cursor_context.md](../cursor_context.md) — agent handoff  
