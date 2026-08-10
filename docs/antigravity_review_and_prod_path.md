# Career OS — Post-Antigravity Review & Prod Path

**Date:** 2026-08-10  
**Audience:** you + next Cursor/Antigravity session  
**Goal:** turn the new Simple Mode shell into something closer to **AI Optim Hire / daily job OS**, then harden for production.

---

## What Antigravity actually shipped

### Good (keep)

| Area | What exists |
|------|-------------|
| Simple / Advanced nav | `modeStore` + `WorkspaceNav` toggle; home → `/inbox` |
| Product pages | Inbox, Discovery, Jobs, Resumes, Companies, Recruiters, Outreach |
| APIs | `/inbox/summary`, `/companies`, `/recruiters`, `/messages` |
| Pipeline | Graph adds Recruiter Discovery → Outreach Draft |
| Agents | `job_discovery_agent`, `recruiter_discovery_agent`, `outreach_draft_agent` |
| Advanced Workspace | Canvas / Vault / Tracker / Approvals still intact |

This is the right **IA**. It is not yet a finished product.

### Honest score

| Layer | Score | Note |
|-------|------:|------|
| Advanced agent workspace | 7.5–8/10 | Still the strongest part |
| Simple Mode product | 4–5/10 | Routes + UI; thin/mocked backends |
| Optim Hire–class daily OS | 3/10 | Missing persistence, truthfulness, ops |
| Production readiness | 3–4/10 | Secrets, CORS, stubs, thin tests |

---

## Critical gaps (fix before new features)

### 1. Persistence bridge (biggest product bug)

Canvas/graph produces recruiter + outreach JSON in **workflow state**, but pages read **Postgres**.

- Graph does **not** write `DBCompany` / `DBRecruiter` / `DBMessage`
- Result: Companies / Recruiters / Outreach often look empty after a “successful” run

**Fix:** after Recruiter Discovery / Outreach Draft (or on Approvals), upsert rows scoped to `user_id` + `job_id` / `application_id`.

### 2. Data isolation

`GET /companies` and `GET /recruiters` return **all rows**, not “mine”.

**Fix:** filter by owning user (via job/application join or `user_id` column).

### 3. Career Inbox is a counter, not a coach

Today: wishlist / ready / total counts; `pending_approvals` hardcoded `0`.

Optim Hire morning experience needs:

- One **recommended next action** (job + why + deep link)
- Real pending approvals
- Follow-ups due (from `DBMessage`)
- High ATS matches from real scores
- **No fake metrics**

### 4. Truthfulness / trust

| Claim | Reality | Prod rule |
|-------|---------|-----------|
| Auto-apply | Playwright navigation **commented out**; sleeps + returns success | Hide or label “experimental stub” — never ship as apply |
| Recruiter emails | Often LLM/`careers@` guesses | Mark confidence; never auto-send |
| LinkedIn | Copy URL only | Keep — do **not** automate |
| Resume ATS on Studio | Mock fallbacks on API failure | Show error, not fake 92% |
| LLM failures | Fall back to mock silently | Surface “mock fallback” in UI |

### 5. Prod hygiene

- Rotate / require strong `SECRET_KEY`; no demo passwords in prod
- Lock CORS to real origins (not `*`)
- Disable `/auth/demo` + `/auth/credentials` outside `ENVIRONMENT=development`
- Portable `RESUME_SOURCE_DIR` (volume mount, not a personal Windows Downloads path)
- Add `beautifulsoup4` to `requirements.txt` if discovery uses it
- Expand tests beyond health/scrape; CI must cover inbox + messages
- Commit the Antigravity working tree so deploys match reality

---

## What “like AI Optim Hire / job portals” means here

Job portals optimize **supply** (listings). Optim Hire–style tools optimize **your apply loop**.

Your winning daily loop should be:

```text
Discover / Import
  → Score (ATS + fit)
  → Tailor resume + cover (HITL)
  → Package on disk
  → Outreach drafts (approve → copy/send)
  → Tracker stages
  → Inbox tells you what’s next tomorrow
```

You already have pieces of each. Glue + honesty > more pages.

---

## Recommended build order (next 4 PRs)

### PR A — Make Simple Mode real ✅ (2026-08-10)

- Persist company / recruiter / message after graph nodes (`workflow_persistence.py`)
- User-scoped `/companies` and `/recruiters`
- Inbox: real `pending_approvals`, `outreach_drafts`, `next_action`
- AutoApplyBot returns stub failure (no fake success)
- Resume Studio no longer injects fake Stripe ATS rows

### PR B — Optim Hire morning UX ✅ (2026-08-10)

1. Inbox hero: “Recommended: Apply to {Company} ({ats}%)” + Canvas / Package / Outreach buttons  
2. Discovery → one-click **Add to Wishlist** (honest ingest; no fake auto-apply)  
3. Jobs card actions: Canvas / Package / Outreach  
4. Collapse Simple nav (Inbox, Jobs, Resumes, Tracker, Outreach, Approvals; rest under More)

### PR C — Resume Studio that feels premium ✅ (2026-08-10)

1. Real version list from `resume_versions` (+ workflow drafts) via `GET /resumes/studio`  
2. Side-by-side original vs tailored (`GET /resumes/studio/{id}`) — no mock scores  
3. Download DOCX/PDF only from successful package (`GET /documents/package-download`)  
4. ATS breakdown from workflow evidence (score / matching / missing / recommendation)

### PR D — Prod harden ✅ (2026-08-10)

1. Secrets + CORS + disable demo auth / seed in prod compose  
2. SMTP optional — send returns mailto, keeps Draft when unset  
3. Logging + `GET /llm/telemetry` for mock fallbacks  
4. Tests: inbox, ingest→Wishlist, message send honesty  
5. `implementation_plan.md` phases 18–23 marked complete  

**Do not prioritize yet:** real Greenhouse auto-submit, LinkedIn automation, K8s, paid marketplace.

---

## Product positioning (so you don’t overclaim)

**Ship as:** “AI career OS — tailor, approve, package, outreach drafts.”  
**Do not ship as:** “Auto-applies to every job board like a human.”

Optim Hire users trust tools that **prepare** applications and **queue** outreach. Silent fake applies destroy trust.

---

## Immediate checklist for you

- [ ] Commit Antigravity changes (or stash) so work isn’t lost  
- [ ] Run one full Canvas job → confirm Companies/Recruiters/Outreach stay empty (repro gap)  
- [ ] Implement PR A persistence  
- [ ] Turn off marketing of AutoApplyBot until real + audited  
- [ ] Switch LLM to Ollama GPU for demos when OpenAI quota is dead  
- [ ] Refresh user-facing docs after PR A  

---

## Bottom line

Antigravity built the **right product shell**. Career OS will feel like Optim Hire when:

1. Every agent output **lands in the pages users open every morning**  
2. Inbox answers **“what should I do next?”** with real data  
3. You never show success for mocked apply/ATS  
4. Prod config stops looking like a local demo  

**Apply loop (2026-08-10):** see `docs/optim_hire_apply_loop.md` — Review & Apply pipeline on Inbox + follow-up drafts ~3 days after marking Applied.

Start with a full E2E smoke (import → Canvas → Approvals → package → outreach → mark Applied → follow-up) when ready.
