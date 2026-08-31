# Loop Engineer v1

**Date:** 2026-08-31

Loop Engineer is Career OS’s approval-gated “loop” for job search:

1. **Company watchlist** — Vault `company_watch` entities + `/loop` UI  
2. **Deep search** — DuckDuckGo `site:` on careers URLs, then Vault portals + boards + open web  
3. **LLM scoring** — Ollama (`qwen2.5:3b`), Kimi K3 free, or DeepSeek via Token Harbor  
4. **Scheduled scans** — APScheduler tick every 30 min (configurable); runs due users only  
5. **Pipeline gates** — scans stop at `awaiting_shortlist`; you approve in `/pipeline`  
6. **Inbox digest** — pending pipeline runs + last scan summary  

**Not included (by design):** silent apply, LinkedIn auto-submit, autonomous resume/portfolio rewrites.

## Quick start

1. **LLM** — In `/loop`, pick **Ollama** (local) or **Token Harbor** (Kimi/DeepSeek free).  
2. **Watchlist** — Add companies + Greenhouse/Lever/Ashby careers URLs, or seed examples.  
3. **Schedule** — Enable scans, set interval (hours), optional “watchlist only”.  
4. **Run now** — Triggers `POST /api/v1/loop-engineer/run-now` → Search Pipeline scan.  
5. **Pipeline** — Approve shortlist → evaluate → prepare → apply/email (same as manual Pipeline).  
6. **Inbox** — Digest shows pending approvals and last scan stats.

## API

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/loop-engineer/status` | Watchlist + schedule + LLM + digest |
| GET/POST/DELETE | `/api/v1/loop-engineer/watchlist` | Company watch CRUD |
| GET/PUT | `/api/v1/loop-engineer/schedule` | Schedule config |
| POST | `/api/v1/loop-engineer/run-now` | Immediate scan |
| GET | `/api/v1/loop-engineer/digest` | Digest lines only |

## Config (backend `.env`)

```env
LOOP_ENGINEER_ENABLED=true
LOOP_ENGINEER_INTERVAL_HOURS=24
LOOP_ENGINEER_TICK_MINUTES=30
LOOP_ENGINEER_DIR=./data/loop_engineer
OLLAMA_MODEL=qwen2.5:3b
# or Token Harbor for Kimi/DeepSeek:
TOKENHARBOR_API_KEY=...
TOKENHARBOR_MODEL=kimi-k3:free
```

## Data layout

```
data/loop_engineer/{user_id}/schedule.json   # enabled, interval, last_run_*
data/pipelines/{user_id}/{run_id}.json       # pipeline runs (shared with /pipeline)
Vault wiki: entity_type=company_watch        # watchlist companies
```

## Daily loop (with Loop Engineer)

```
/loop (schedule + watchlist) → scan → auto packets → email/Inbox notify
→ /loop review packet → Confirm → /apply (gates) → /tracker
```

Alternative bulk path: `/pipeline` (shortlist → evaluate → prepare → execute).

Resume updates remain in **Tailor / Studio** — Loop Engineer builds a **preview** in each packet; confirm copies it into the application workflow state.

See also: `docs/loop_engineer_roadmap.md` for v3–v5 plan (push, Slack, portfolio, autofill).

## Ollama models (12 GB disk)

```bash
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
```

Optional: `deepseek-r1:1.5b` for reasoning-heavy scoring (slower).
