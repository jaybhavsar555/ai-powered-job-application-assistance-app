# Research: Tsenta — what to copy (and what not to)

**Date:** 2026-08-13  
**Sources:** [tsenta.com](https://tsenta.com/), [AI agent page](https://tsenta.com/ai-agent), [AI disclosure](https://tsenta.com/ai-disclosure), [Developers API](https://tsenta.com/developers)

---

## 1. What Tsenta actually is

Marketing: *“AI agent that auto-applies. Be applicant #4, not #247.”*

**Product loop (four stages):**

| Stage | What they sell | How it likely works |
|-------|----------------|---------------------|
| **Find** | Watch 50,000+ *company career pages* (Workday, Greenhouse, Lever, Ashby + 15) | Continuous crawl / ATS job-index polling — **not** LinkedIn/Indeed as primary |
| **Prep** | Per-role résumé + cover, keyword-aligned, **diff before send** | LLM rewrite from uploaded résumé facts only |
| **Apply** | Login, fill every field, open-ended Qs in your voice, upload, submit | Server-side or browser bot across ~19 ATSes; overlay or headless |
| **Track** | Recruiter replies auto-routed; Applied → Viewed → Replied → Interview | Inbox parsing + status machine |

**Surfaces:** web dashboard, Chrome extension, iMessage/WhatsApp (“yes” to apply), iOS/Android, desktop, **MCP/CLI**.

**Pricing:** 25 free apps, then pay **per submitted volume** ($19 / 600, $39 / 1,500, $99 / 4,500). Failed apps not charged (API: $0.09/submit).

**Trust UX (their real differentiator vs LazyApply):**

- Diff of résumé changes — nothing sent silently  
- **Receipt** per application: fields filled, answers, résumé version, timestamp  
- Work-auth / OPT / sponsorship filter  
- Review-before-submit option on the developer API  

---

## 2. Career OS vs Tsenta (honest gap)

| Tsenta capability | Career OS today | Copy? |
|-------------------|-----------------|-------|
| Career-page / ATS-first discovery | Vault `job_portal` KBs + Remotive/RemoteOK/Arbeitnow | **Yes** — add ATS hosts to Vault, keep quality ranking |
| Match % + why it matched | Discovery `matchScore` / `matchReason` | Already have — keep prominent |
| Paste any job URL | Jobs ingest + Quick Apply | Already have |
| Per-role tailor + cover | Tailor + Canvas + package | **Stronger** than Tsenta’s add-on-free claim |
| Diff before send | Tailor comparison / Approvals | Already have — keep as gate |
| Approve before send | Review & Apply + Approvals | **Keep as default** (Tsenta’s volume mode is opt-in) |
| ATS form fill | Extension Greenhouse/Lever/Workday fill | Partial — Review mode only |
| Headless Workday submit in 2–3s | Not claimed | **Do not copy** (ToS, bans, quality) |
| Application **receipt** | Review & Apply Form tab + receipt banner after Confirm submitted | **Shipped** |
| Recruiter reply auto-route | Outreach + Inbox digest, no email ingest | Later (needs mailbox OAuth) |
| Work-auth / sponsorship | Screening Q&A seed only | **Yes — first-class pref** |
| iMessage “yes” to apply | — | Skip (volume/quality conflict) |
| MCP apply API | — | Optional later; not the wedge |
| Volume 4,500 apps/month | Gated Auto + rate limits | **Do not copy marketing** |

**Our wedge vs Tsenta:** quality-first *tailor → approve → package → outreach/follow-up*, then autofill. Tsenta’s wedge is *speed to first 100 applicants* via career-page crawl + silent submit.

---

## 3. Architecture we will **not** clone

```text
50k career-page crawler  →  match in seconds  →  headless ATS login/submit
```

Hard parts: per-ATS account pools, captchas, Workday multi-page, employer ToS, LinkedIn bans, fake-volume quality. Career OS already chose **Review & Apply + gated Auto** after OptimHire research (`docs/competitor_auto_apply_research.md`).

---

## 4. What to copy (phased)

### Phase T1 — Tsenta UX, Career OS engine (this pass)

1. **Application receipt** after Confirm submitted (fields, answers, resume, time).  
2. **Work authorization** as a saved pref (citizen / OPT / needs sponsorship) → extension profile + Discovery filter hint.  
3. **ATS career-page portals** in Vault (Greenhouse, Lever, Ashby, Workday) so Find uses the same *source class* Tsenta markets.  
4. Inbox copy: **Find → Prep → Apply → Track** as the four-stage story (detailed steps stay underneath).

### Phase T2 — next

- Saved tailored résumé **per company** (reuse on second role).  
- Tracker columns aligned to Tsenta: In flight / Needs you / Failed / Skipped.  
- Extension overlay: “Auto-fill ready · N fields detected” + receipt after user Submit.  
- Daily curated match list (Inbox digest already exists — surface match %).

### Phase T3 — only if we change positioning

- Continuous career-page watch (cron + allowlisted company URLs from Vault, **not** 50k).  
- Headless submit — still gated, never LinkedIn-first.

---

## 5. Positioning line

> Tsenta watches career pages and submits at volume.  
> Career OS **finds on those same ATS/portals, rewrites from your facts, shows the diff, and records a receipt — you click Submit.**

Do not claim “applicant #4 in 2 seconds.” Claim “first-wave *quality* apply with a paper trail.”
