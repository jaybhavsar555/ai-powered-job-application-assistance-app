# Career OS Chrome extension (Phase B fill + Phase C gated Auto)

Full stack setup (Docker API + local Next.js): see root [README.md](../README.md).

## Modes

| Mode | Behavior |
|------|----------|
| **Review & Apply** (default) | Fill Greenhouse / Lever / Workday fields **and attach resume** when a file input exists. **You** click Submit. |
| **Auto Apply** (gated) | Fill + resume attach + click Submit only when: explicit consent, host allowlist, confidence ≥ threshold, under hourly/daily rate limits. |

**Never** auto-submits LinkedIn (blocklist). Captcha / login / missing answers → skip event → Tracker `Needs input` or `Failed` → fix → `Reapply`.

## Load unpacked

1. Backend `:8001` + web app login  
2. Copy JWT  
3. `chrome://extensions` → Load unpacked → this folder  
4. Popup: API `http://localhost:8001/api/v1` + token → Save  
5. Optional: check consent → Save → **Fill + Auto Submit** on allowlisted ATS  

## APIs

- `GET /extension/profile` — profile + prefs + resume metadata  
- `GET /extension/resume-file` — streams tailored package PDF/DOCX (or library base) for ATS upload  
- `POST /extension/events` — evaluate / filled / submit_attempt / submitted / skip / reapply  
- `PUT /apply-prefs/` — Review vs Auto + consent  

## Resume upload

On Fill, the extension fetches `/extension/resume-file` and sets `input[type=file]` via `DataTransfer` (Greenhouse / Lever / many Workday skins). Prefer a Quick Apply or Package run so the tailored PDF is used; otherwise the base file under `data/resumes/` is used.

Some custom dropzones ignore programmatic files — if the toast says attach failed, upload that file manually.

## Honest limits

- **Gmail / mailto cannot auto-attach PDFs** (browser security). Use Quick Apply → Download PDF & open Gmail, then paperclip.  
- Workday skins vary — confidence gate may refuse Submit  
- Server never drives a headless browser; extension is the apply engine  
