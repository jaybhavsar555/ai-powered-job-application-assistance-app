# Optim Hire–style apply loop (Career OS)

**Date:** 2026-08-10

## How Optim Hire does it

1. Profile + preferences  
2. AI finds matching jobs  
3. Tailors resume / cover per JD  
4. **Two modes:** Auto-Apply (extension fills + submits) vs **Review & Apply** (you approve)  
5. Track applied jobs  
6. (Their extension) handles forms on partner boards when logged in  

They still need: browser login, captchas, and human review for many sites. They do **not** magically bypass every board.

## How Career OS mirrors that (honest)

| Step | Optim Hire | Career OS |
|------|------------|-----------|
| Discover | Scans boards / partners | Discovery (Remotive + LLM) or Vault portal → copy URL → Import |
| List with JD + link | My Jobs | Jobs / Tracker (+ package files) |
| Tailor | AI resume / cover | Canvas: ATS → Resume Optimizer → Cover Letter |
| Review | Review & Apply | Approvals HITL |
| Package | Upload resume | Apply package DOCX/PDF |
| Submit | Extension / auto | **You** open job link + upload (no fake success) |
| Track | Dashboard | Tracker stages → mark **Applied** |
| Follow-up | Manual / product features | Auto-**draft** human-tone FollowUp ~3 days later → Outreach send |

**Apply mode we ship:** `review_and_apply` (see Inbox banner). Full Greenhouse/LinkedIn auto-submit remains out of scope until a real audited browser agent exists.

## Daily path for you

1. Inbox → see recommended step + Apply loop rail  
2. Discovery / Vault → build wishlist with JD + site link  
3. Canvas Simulate → tailor (optional before apply)  
4. Approvals → Package  
5. **Review & Apply** (`/apply`) — open employer site, map form fields, **approve each gate**, you click Submit on their site  
6. Confirm submitted → Applied + follow-up draft (~3 days) → Outreach  

## Review & Apply studio

- API: `/api/v1/apply-sessions/*`  
- UI: `/apply?job_id=…`  
- Mode: same idea as Optim Hire **Review & Apply** (not silent Auto-Apply)  
- Showcase: browser chrome + field fill progress; real site opens in a new tab (ATS pages block iframes)  

## Code map

- Pipeline steps + summary: `backend/app/api/v1/endpoints/inbox.py`  
- Apply session: `backend/app/application/services/apply_session.py`  
- Follow-up schedule/draft: `backend/app/application/services/follow_up.py`  
- Apply Studio UI: `frontend/src/app/(workspace)/apply/page.tsx`  
- Trigger on Applied: `ApplicationService.update_stage`  
- Inbox UI: `frontend/src/app/(workspace)/inbox/page.tsx`  
