# Career OS Chrome extension (Phase B fill + Phase C gated Auto)

## Modes

| Mode | Behavior |
|------|----------|
| **Review & Apply** (default) | Fill Greenhouse / Lever / Workday fields. **You** click Submit. |
| **Auto Apply** (gated) | Fill + click Submit only when: explicit consent, host allowlist, confidence ≥ threshold, under hourly/daily rate limits. |

**Never** auto-submits LinkedIn (blocklist). Captcha / login / missing answers → skip event → Tracker `Needs input` or `Failed` → fix → `Reapply`.

## Load unpacked

1. Backend `:8001` + web app login  
2. Copy JWT  
3. `chrome://extensions` → Load unpacked → this folder  
4. Popup: API `http://localhost:8001/api/v1` + token → Save  
5. Optional: check consent → Save → **Fill + Auto Submit** on allowlisted ATS  

## APIs

- `GET /extension/profile` — profile + prefs  
- `POST /extension/events` — evaluate / filled / submit_attempt / submitted / skip / reapply  
- `PUT /apply-prefs/` — Review vs Auto + consent  

## Honest limits

- Resume file upload still manual  
- Workday skins vary — confidence gate may refuse Submit  
- Server never drives a headless browser; extension is the apply engine  
