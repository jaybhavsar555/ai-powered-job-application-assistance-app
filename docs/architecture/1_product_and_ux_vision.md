# Product Requirements Document (PRD) & UX Vision

## 1. Product Vision
Career OS is a **Career Operating System**: persistent Knowledge Vault, observable multi-agent workflows, and human-in-the-loop approvals — not a black-box resume spinner.

### Core Principles
1. **AI Observability** — Canvas, Inspector, Terminal, and Analytics expose agent work.  
2. **Human-in-the-Loop** — Approvals use Git-style diffs before committing resume/letter changes.  
3. **Knowledge Accumulation** — Wiki entities + Qdrant memory compound over time.  
4. **Local-first option** — Ollama by default; OpenAI optional.

## 2. Information Architecture (shipped)

| Workspace | Route | Role |
|-----------|-------|------|
| AI Canvas | `/canvas` | Visual agent execution + SSE |
| Knowledge Vault | `/vault` | Entities + semantic search |
| Approvals | `/approvals` | Diff inbox for AI drafts |
| Tracker | `/tracker` | Kanban application CRM |
| Analytics | `/analytics` | Cost / tokens / success / pipeline |

Layout: left nav · center main · right Inspector · bottom Terminal (`WorkspaceLayout`).

## 3. UX journeys

### Intake → Canvas
1. User starts a workflow from Canvas (job id).  
2. Nodes light up via SSE (`AGENT_STARTED` / `SUCCESS`).  
3. Inspector shows latency, tokens, evidence.  

*(Phase 10: Tracker **Import job** → `POST /jobs/ingest` scrapes URL via Playwright, with httpx/mock fallback.)*

### Approval
1. Workflow completes → `final_state` in store.  
2. Approvals page renders cover letter + resume keyword diffs.  
3. Approve / Reject persists CoverLetter / ResumeVersion and can advance stage to Ready.

### Vault memory
1. User adds skill/story/project (or agents write entities later).  
2. System embeds + indexes in Qdrant.  
3. Semantic search finds related memories.

### Tracker
1. Job ingest creates Wishlist card.  
2. Drag across stages; optimistic UI + PATCH stage.

## 4. Wireframe (current)

```text
+----------+---------------------------+----------------+
| Nav      |  Main (route content)     | Inspector      |
| Canvas   |                           | telemetry /    |
| Vault    |  Canvas | Vault | Board   | evidence       |
| Approvals|                           |                |
| Tracker  |                           |                |
| Analytics|                           |                |
+----------+---------------------------+----------------+
| Terminal log (SSE / agent prints)                     |
+-------------------------------------------------------+
```

## 5. Non-goals (near term)
- Fully automated apply-without-approval  
- Replacing LinkedIn as a social network  
- Guaranteed GPU performance on CPU-only Ollama hosts  
