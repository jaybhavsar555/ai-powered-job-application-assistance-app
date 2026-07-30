# Career OS — Simple Mode & Career Inbox Roadmap

**Status:** Spec only — **not implemented** (as of 2026-07-31).  
**Rule:** Do **not** remove or rewrite the existing Advanced Workspace. Extend on top.

This document turns the product critique (“engineering dashboard vs morning job-search OS”) into a phased build plan grounded in the **current codebase**.

Related: [user_guide.md](./user_guide.md) · [implementation_plan.md](./implementation_plan.md) · [architecture_design.md](./architecture_design.md)

---

## Verdict (honest)

| Layer | Reality |
|-------|---------|
| Advanced AI Workspace | **Shipped** (~7.5–8/10 as an agent/devtools product) |
| Simple Mode / daily product | **Missing** |
| Career Inbox (“what should I do today?”) | **Missing** |

We did **not** implement the Cursor product prompt. Nothing from Advanced Mode was deleted — the second product layer was simply never added.

Home still `redirect('/canvas')`. Real nav is `WorkspaceNav` (Canvas / Vault / Approvals / Tracker / Analytics / Marketplace).  
`frontend/src/components/layout/Sidebar.tsx` lists Dashboard/Jobs/Resumes but is **unused** dead UI — not the live shell.

---

## Gap matrix vs product prompt

### Built today (keep — becomes Advanced Workspace)

| Prompt item | Code reality | Notes |
|-------------|--------------|-------|
| AI Canvas + workflow stream | Yes | `/canvas`, SSE, React Flow |
| Node Inspector + timeline / logs | Partial–Yes | `InspectorPanel`, `TerminalLog`, timeline |
| Knowledge Vault | Yes | Entities + search + portal seed; **no** graph UI |
| Human Approvals | Yes | `/approvals` |
| Tracker Kanban | Yes | Wishlist → … → Rejected (fewer stages than prompt) |
| Analytics | Partial | Summary telemetry; no offer/reply rates |
| Job import URL + paste JD | Yes | Tracker `JobIngestForm` → `POST /jobs/ingest` |
| Package DOCX/PDF | Yes | Apply-package after dual approval |
| Marketplace, LLM switch, durable checkpoints | Extra | Beyond that prompt |

### Not built (Simple Mode product)

| Prompt item | Status | Existing hooks |
|-------------|--------|----------------|
| Simple vs Advanced mode toggle | No | — |
| Career Inbox / Today dashboard | No | Could aggregate applications + approvals + ATS |
| Resume Studio (diff, versions, ATS UI) | No | `DBResume` / `DBResumeVersion` + package APIs |
| Companies page | No | `DBCompany` table exists; rarely populated |
| Recruiters page | No | `DBRecruiter` stub |
| Outreach drafts + human approval | No | `DBMessage` stub (`Draft` status) |
| Gmail / Outlook OAuth send | No | Optional backlog |
| LinkedIn find + copy (no automation) | No | Recruiter URL fields only |
| PDF / screenshot / email / extension import | No | Text + URL only |
| Auto-start pipeline after import | No | Manual Simulate |
| Recruiter discovery graph node | No | Pipeline ends at Cover Letter |
| Richer analytics (offer, reply, cost explorer) | No | Partial agent logs only |
| Prompt / Model / Cost explorers | No | Fragments in Inspector |

---

## Product principle

```text
┌─────────────────────────────────────────────┐
│  SIMPLE MODE (default)                      │
│  Dashboard · Jobs · Resume · Companies ·    │
│  Recruiters · Outreach · Interviews ·       │
│  Tracker · Vault · Approvals · Analytics    │
└─────────────────────────────────────────────┘
                    │ deep-links into
                    ▼
┌─────────────────────────────────────────────┐
│  ADVANCED WORKSPACE (preserved)             │
│  Canvas · Inspector · Logs · Marketplace ·  │
│  LLM switch · Checkpoints · Prompt edit     │
└─────────────────────────────────────────────┘
```

Like VS Code: debugger exists, but beginners open the editor first.

**Unique wedge:** Career Inbox — every morning answers:

- What should I do today?
- Which jobs to apply to?
- Which follow-ups are due?
- Which resume version to use?
- One recommended next action + ETA

---

## Target IA (sidebar)

### Simple Mode

| Nav | Route (proposed) | Purpose |
|-----|------------------|---------|
| Dashboard | `/inbox` or `/dashboard` | Career Inbox home |
| Jobs | `/jobs` | Import + job cards (list/grid) |
| Resume Studio | `/resumes` | Versions, diff, ATS, download |
| Companies | `/companies` | Research cards from pipeline |
| Recruiters | `/recruiters` | People + LinkedIn copy actions |
| Outreach | `/outreach` | Drafts awaiting approval |
| Interviews | `/interviews` | Schedule + notes |
| Tracker | `/tracker` | Existing Kanban (**keep**) |
| Knowledge Vault | `/vault` | Existing (**keep**) |
| Approvals | `/approvals` | Existing (**keep**) |
| Analytics | `/analytics` | Existing + extend |

### Advanced Workspace (group / footer)

| Nav | Route | Purpose |
|-----|-------|---------|
| AI Canvas | `/canvas` | Existing |
| Workflow Inspector | `/canvas` + inspector | Existing panel; optional dedicated route later |
| Execution Logs | terminal / `/logs` | Promote `TerminalLog` |
| Prompt Inspector | canvas inspector | Existing |
| Model Inspector | `/settings/llm` | Promote LLM switch |
| Cost Explorer | `/analytics/cost` | New |
| Settings | `/settings` | Profile, mode default, paths |
| Marketplace | `/marketplace` | Existing |

Default home: **`/inbox`** (not `/canvas`). Advanced users can set “Open Canvas on launch” in Settings.

---

## Phased implementation (do in order)

### Phase 18 — Shell + Career Inbox (highest leverage)

**Goal:** Morning product without touching agent graph.

**Frontend**

- [ ] Mode toggle: `simple` | `advanced` (Zustand + `localStorage`)
- [ ] Split `WorkspaceNav`: Simple items first; Advanced section collapsed by default in Simple mode
- [ ] New `/inbox` (Dashboard) page
- [ ] Redirect `/` → `/inbox` (Advanced preference → `/canvas`)
- [ ] Wire cards to real data only (no fake Stripe metrics)

**Inbox widgets (v1 — compute from what we already have)**

| Widget | Source |
|--------|--------|
| Applications today / this week | `applications.created_at` / stage changes |
| Pending approvals | Approvals queue / workflow_state flags |
| Wishlist / Ready counts | Tracker stages |
| High ATS matches | Latest `ats_score` on application / resume_versions |
| Recently optimized resumes | `resume_versions` / package paths |
| Recommended next action | Heuristic: highest ATS in Wishlist/Ready without package |
| Today's AI suggestions | Static rules first (“Import 1 job”, “Approve drafts”) |

**Backend**

- [ ] `GET /api/v1/inbox/summary` aggregating the above
- [ ] Optional: `GET /inbox/next-action`

**Explicitly out of Phase 18:** OAuth, LinkedIn scrape, new graph nodes.

**Acceptance**

- Login as Jay → land on Inbox that reflects **real** Wishlist cards (e.g. CareerForge / Nimbus jobs)
- One CTA opens Tracker or Canvas for that `job_id`
- Advanced Mode still shows full current nav; Canvas unchanged

---

### Phase 19 — Jobs page (Simple Mode home for import)

**Goal:** Jobs as first-class product surface; Tracker remains Kanban.

- [ ] `/jobs` list/grid of `GET /jobs/` + application stage
- [ ] Job card: company, role, location (from normalized JD), ATS, status, actions
- [ ] Import UX: URL + paste JD (reuse ingest); Advanced: “Open in Canvas”
- [ ] Optional: “Start workflow after import” checkbox → SSE stream for new `job_id`
- [ ] Later imports: PDF text extract, screenshot OCR, email forward, extension (separate epics)

**Acceptance:** Import from `/jobs` creates Wishlist card identical to Tracker ingest.

---

### Phase 20 — Resume Studio

**Goal:** Human-facing resume product on top of versions + packages.

- [ ] `/resumes` — library from `GET /documents/resume-library` + DB resumes
- [ ] Per application: original vs tailored, ATS breakdown, approve/reject (deep-link Approvals)
- [ ] Diff viewer (JSON/bullets)
- [ ] Download DOCX/PDF (existing apply-package / export)
- [ ] Version history list from `resume_versions`

**Do not** replace Approvals — Studio is the friendly surface; Approvals stay for HITL.

---

### Phase 21 — Companies & Recruiters

**Goal:** Persist research outputs into browsable pages.

- [ ] On company_research success → upsert `DBCompany.research_data`
- [ ] `/companies` list + detail
- [ ] `DBRecruiter` CRUD (manual add first)
- [ ] `/recruiters` — name, email, LinkedIn URL
- [ ] Actions: **Copy** message, **Open LinkedIn**, **Open job** — **never** auto-send / auto-connect

---

### Phase 22 — Outreach + Career Inbox reminders

**Goal:** Draft → approve → mark sent (no silent sends).

- [ ] After cover approval, generate draft messages into `DBMessage` (LinkedIn connect, recruiter note, follow-up)
- [ ] `/outreach` queue: Copy / Open Gmail / Mark Sent / Snooze
- [ ] Follow-up due dates on messages → Inbox “Pending follow-ups”
- [ ] OAuth Gmail/Outlook = **Phase 24+** (draft + copy works without OAuth)

---

### Phase 23 — Pipeline extensions (Advanced + Simple)

**Goal:** Longer graph without breaking checkpoints.

- [ ] Optional nodes after cover: Recruiter Discovery → Outreach Draft (HITL gates)
- [ ] Auto-start workflow after import (user setting)
- [ ] Tracker stages: add `OA`, `Offer`, `Archived` (migrate carefully)
- [ ] Richer Node Inspector fields: cost, confidence, retry, related docs (no chain-of-thought)

---

### Phase 24 — Integrations & analytics depth

- [ ] Gmail OAuth draft/send with approval
- [ ] Outlook OAuth
- [ ] Browser extension / email-forward ingest
- [ ] Analytics: success rate, interview rate, offer rate, recruiter reply rate, token/cost explorer
- [ ] Vault: relationship graph UI, timeline, typed collections (skills, projects, notes)

---

## Career Inbox mock (target UX)

```text
🔔 Good morning, Jay

Today
• N wishlist jobs
• M ready to apply (package done)
• K pending approvals
• F follow-ups due (when Outreach exists)
• I interviews (when Interviews exists)

Recommended next action
→ Apply to {Company} — {Role} ({ats}% ATS)
Estimated time: ~8 minutes
[ Open Tracker ] [ Run Canvas ] [ Package ]
```

v1 numbers must come from Postgres for the logged-in user — never hard-coded marketing fake data.

---

## Non-goals / guardrails

1. **Never delete** Canvas, Vault, Approvals, Tracker, Analytics, Marketplace, Inspector, SSE.
2. **Never automate LinkedIn** actions (ToS). Copy + open profile only.
3. **Never send email** without explicit approval (and later OAuth consent).
4. Prefer **deep-links** into existing pages over duplicating Approvals/Canvas logic.
5. Schema stubs (`companies`, `recruiters`, `messages`) — **use them**; don’t invent parallel tables without migration.
6. Keep API on **8001**; document new routes in OpenAPI.

---

## Suggested first PR slice (smallest shippable)

1. `GET /inbox/summary`
2. `/inbox` page with 4–6 real widgets
3. Nav: Dashboard + Advanced group; `/` → `/inbox`
4. Mode toggle (Simple hides Canvas/Marketplace/Analytics detail links or groups them)

Estimate: 1–2 focused sessions. Unblocks the “product vs dashboard” perception without rewriting agents.

---

## Mapping prompt “after import” pipeline

Prompt ideal:

```text
Intake → Research → ATS → Resume → Approval → Cover → Approval
→ Recruiter Discovery → Approval → Done
```

**Today:** Intake → Research ∥ ATS → Resume → Cover → (Approvals UI outside graph) → Package.

**Delta to implement later (Phase 23):** move dual approval gates into graph optional interrupts; add recruiter discovery node; keep Approvals page as inbox for pending interrupts.

---

## Checklist for implementers

Before coding a phase:

- [ ] Confirm Advanced routes still work unchanged
- [ ] Add/extend API with auth (`get_current_user`)
- [ ] Simple UI consumes API — no mock Stripe cards in production builds
- [ ] Update [user_guide.md](./user_guide.md) for new routes
- [ ] Tick phase boxes in [implementation_plan.md](./implementation_plan.md)

---

## Summary

| Question | Answer |
|----------|--------|
| Did we implement the product prompt? | **No** |
| Did we miss deleting features? | **No** — Advanced Workspace is intact |
| What’s the gap? | Simple Mode + Career Inbox + Resume/Outreach product layer |
| What to build first? | **Phase 18 — Inbox + nav mode** |
| What makes Career OS unique? | Morning **Career Inbox** with one recommended next action |
