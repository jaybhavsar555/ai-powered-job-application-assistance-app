# Loop Engineer — 24/7 roadmap

**Date:** 2026-08-31

This document is the plan for evolving Career OS into a **24/7 loop** that searches, researches, tailors, notifies you, and applies **only after you confirm** each job.

---

## Version map

| Version | Status | What it does |
|---------|--------|----------------|
| **v1** | Shipped (PR #4) | Company watchlist, scheduled scans, Pipeline approval gates, Inbox digest, Ollama/Kimi scoring |
| **v2** | Shipped (this branch) | **Job packets** per role: JD + company research + resume/cover preview; email notify; **Confirm → Review & Apply** |
| **v3** | Planned | Push notifications (mobile/web), Slack digest, packet batch review UI, auto-package DOCX/PDF on confirm |
| **v4** | Planned | Portfolio sync stub (static site export from approved resume JSON) |
| **v5** | Planned | Extension auto-fill after confirm on allowlisted ATS only (still no LinkedIn silent submit) |

---

## Your target flow (confirm-then-apply)

```
┌─────────────────────────────────────────────────────────────────┐
│  24/7 LOOP (background)                                         │
│  Watchlist → scan boards + careers pages → score (Ollama/Kimi)  │
│  → build packet (research + tailor preview) → notify you        │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  YOU REVIEW (email + /loop + Inbox)                             │
│  JD · company research · match % · tailored resume · cover      │
│  [Confirm]  [Skip]                                              │
└────────────────────────────┬────────────────────────────────────┘
                             ▼ Confirm only
┌─────────────────────────────────────────────────────────────────┐
│  APPLY (gated)                                                  │
│  Ingest job → Review & Apply session → extension autofill       │
│  You approve each gate → you click Submit on employer site      │
└─────────────────────────────────────────────────────────────────┘
```

**Nothing applies or emails without your confirm** on the packet (v2) and gates in `/apply`.

---

## v2 — what shipped

### Backend
- `JobPacketService` — builds packet after scan (match ≥ 70% default)
- `LoopNotifyService` — email when packets ready (SMTP or mock log in dev)
- `POST /loop-engineer/packets/{id}/confirm` — ingest + apply session
- `POST /loop-engineer/packets/{id}/reject` — skip role

### Frontend
- `/loop` — packet list + detail panel (research, resume, cover)
- Schedule toggles: **auto-build packets**, **email notify**

### Config
```env
LOOP_ENGINEER_AUTO_BUILD_PACKETS=true
LOOP_ENGINEER_AUTO_PACKET_MIN_SCORE=70
LOOP_ENGINEER_NOTIFY_EMAIL=true
LOOP_ENGINEER_FRONTEND_URL=http://localhost:3000
SMTP_HOST=...   # optional; without it dev logs mock email
```

---

## v3 plan — better notifications

| Channel | Implementation |
|---------|----------------|
| **Email** | Done (v2) |
| **Telegram** | Done — bot + `/link CODE` webhook |
| **WhatsApp** | Done — Meta Cloud API or Twilio |
| **Inbox** | Done — digest lines link to `/loop` |
| **Browser push** | Planned — service worker |

**Trigger:** after `build_packets_for_run`, call all enabled channels once per batch.

---

## v4 plan — portfolio (lightweight)

- Export approved resume JSON → static Markdown/HTML in `data/portfolio/`
- Optional: GitHub Pages deploy hook (user provides token)
- **Not** live auto-edit of personal site without approval

---

## v5 plan — confirm-then-autofill

After packet confirm + apply session gates:
1. Extension receives `job_id` + `apply_session_id`
2. On allowlisted ATS (Greenhouse/Lever/Workday): fill + attach resume
3. **Auto Submit** only if user enabled gated Auto Apply in Inbox **and** confidence ≥ threshold
4. LinkedIn/Indeed remain blocklisted

---

## 24/7 operation checklist

### Infrastructure (your Docker stack)
```yaml
api      # FastAPI + APScheduler tick
ollama   # qwen2.5:3b + nomic-embed-text
postgres # jobs, applications, vault
redis    # future: Celery beat if you outgrow APScheduler
qdrant   # vault semantic search
```

### Daily operator steps (minimal)
1. Enable schedule in `/loop` (e.g. every 12–24h)
2. Keep watchlist updated
3. Check email or Inbox when notified
4. Review packets in `/loop` → **Confirm** or **Skip**
5. Finish `/apply` gates for confirmed jobs

### Token / cost control
| Setting | Effect |
|---------|--------|
| `watchlist_only=true` | Fewer sources, lower tokens |
| `LOOP_ENGINEER_AUTO_PACKET_MIN_SCORE=80` | Fewer packets built |
| Ollama local | No API cost; uses disk/RAM |
| Kimi/DeepSeek free | Token Harbor daily limits |

### Recommended models (12 GB disk)
- `qwen2.5:3b` — scoring + tailor (fast)
- `nomic-embed-text` — vault search
- Avoid 8B+ local models on tight disk

---

## Two paths to apply (pick one per job)

### Path A — Loop Engineer packet (v2, fastest for you)
`/loop` → review packet → **Confirm** → `/apply` gates

### Path B — Pipeline bulk (v1, more control)
`/pipeline` → shortlist → evaluate → prepare → execute approvals

Both end in **Review & Apply** — no silent board submit.

---

## API quick reference (v2)

```
GET  /api/v1/loop-engineer/packets
GET  /api/v1/loop-engineer/packets/{id}
POST /api/v1/loop-engineer/packets/{id}/confirm
POST /api/v1/loop-engineer/packets/{id}/reject
POST /api/v1/loop-engineer/packets/build-for-run/{run_id}
POST /api/v1/loop-engineer/run-now
```

---

## Honest limits (won’t fake)

| Limit | Why |
|-------|-----|
| LinkedIn auto-apply | ToS / ban risk |
| Captcha / MFA | Needs you in browser |
| 100% autonomous apply | Quality + compliance |
| Portfolio live deploy | v4 scope; needs your hosting |

---

## Next implementation order (if you want v3+)

1. Slack webhook notifier (1 day)
2. Auto-generate DOCX/PDF on packet confirm (`generate_package: true` default)
3. Browser push for packet ready
4. Celery beat if APScheduler isn’t enough for multi-user scale
5. Portfolio static export (v4)
