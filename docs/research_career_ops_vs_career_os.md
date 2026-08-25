# Research: career-ops + ai-job-search vs Career OS

Sources reviewed:

- [career-ops.org/docs](https://career-ops.org/docs) (santifer/career-ops)
- [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search)

## What they do well

### career-ops

| Capability | How it works |
|------------|----------------|
| **Auto-pipeline** | Paste URL → extract JD (Playwright → fetch → web search) → liveness gate → score 1–5 across 5 dimensions + global score → Markdown report → tailored PDF → tracker row |
| **Portal scan** | `/career-ops scan` across 150+ Greenhouse / Ashby / Lever company pages (zero LLM tokens for scrape) |
| **Apply drafts** | Draft Greenhouse/Ashby/Lever form answers from CV + JD — **paste-ready only** |
| **Email / cover** | Draft modes; human sends |
| **Philosophy** | Local-first files; **never auto-submits**; every send is human-approved |

### ai-job-search (Mads Lorentzen)

| Capability | How it works |
|------------|----------------|
| **`/scrape`** | Portal CLIs (Bun) in parallel + WebSearch fallback; dedupe vs seen jobs + tracker; quick fit table |
| **`/apply`** | Eligibility + language gates → 5 scoring dimensions → tailored LaTeX CV + cover → **reviewer agent** critiques → human final |
| **Human loop** | Pick matches from scrape → apply one URL → review before send |
| **Market** | Danish boards by default; portal skills are swappable |

Shared pattern from both: **search → score → draft → human approve → you submit**. Neither product silent-fires applications.

## Career OS today

| Stage | Status |
|-------|--------|
| Vault portals + Remotive/RemoteOK/Arbeitnow + DDG `site:` | Live (`JobDiscoveryAgent`) |
| Open-web search (beyond portal hosts) | Added as `web_search` source |
| Canvas tailor + Approvals + packages | Live |
| Review & Apply session (per-step gates) | Live |
| Outreach drafts + SMTP/mailto | Live |
| Extension autofill (allowlisted ATS) | Live; server auto-submit refused |
| **One guided pipeline with approve-at-each-gate** | **`/pipeline` (this work)** |

## Target Career OS pipeline (inspired by both)

```
1. SCAN      Vault KBs + common boards + open web
2. SHORTLIST User approves which jobs continue
3. EVALUATE  Fit score + gates (auth / location notes)
4. PREPARE   Wishlist ingest + package + email draft
5. EXECUTE   Start Review & Apply and/or send email
             — each action needs explicit approval
```

No silent mass-apply. Aligns with career-ops “nothing leaves without approval” and Mads’ scrape→pick→apply→reviewer loop, while keeping Career OS’s Postgres tracker, Vault, extension, and Ollama/Token Harbor LLMs.
