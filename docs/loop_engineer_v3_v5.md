# Loop Engineer v3–v5 (shipped)

## v3 — Browser push + auto-package + batch review

| Feature | Status |
|---------|--------|
| Web Push notifications | `public/sw.js` + VAPID keys |
| Auto DOCX/PDF on confirm | Default `LOOP_ENGINEER_AUTO_PACKAGE_ON_CONFIRM=true` |
| Batch confirm / skip all | `POST /packets/batch-confirm` |

### Browser push setup

```bash
cd backend && pip install pywebpush
python scripts/generate_vapid_keys.py
```

Add keys to `.env`, restart API, then in `/loop` click **Enable browser notifications**.

---

## v4 — Portfolio static export

On packet confirm (toggle **Update static portfolio**):

- Writes `data/portfolio/{user_id}/index.html` + `profile.json`
- Preview: `GET /api/v1/loop-engineer/portfolio/preview`

Not a live website deploy — export for you to review/host manually.

---

## v5 — Extension apply queue

After confirm:

1. Job added to `extension_apply_queue`
2. Chrome extension polls every 5 min → badge count
3. Open job URL → extension autofill + attach packaged resume
4. `POST /extension/apply-queue/{id}/done` when finished

Extension manifest: `alarms`, `notifications` permissions added.

Profile API includes `loop_engineer_queue.pending_count`.

---

## Full notification matrix

| Channel | Config |
|---------|--------|
| Email | SMTP |
| Telegram | `TELEGRAM_BOT_TOKEN` |
| WhatsApp | `WHATSAPP_PROVIDER=meta` or `twilio` |
| Browser push | VAPID keys |
| Extension badge | Chrome extension + token |

---

## Confirm flow (all versions)

```
Scan → packet → notify (all channels)
→ review /loop → Confirm
→ DOCX/PDF package + portfolio HTML + apply session + extension queue
→ /apply gates + extension on job URL
```
