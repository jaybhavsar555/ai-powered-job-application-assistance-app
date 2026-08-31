# Loop Engineer — Telegram & WhatsApp notifications

Get job packet alerts on your phone when Loop Engineer finishes a scan.

---

## Channels

| Channel | Cost | Setup difficulty |
|---------|------|------------------|
| **Telegram** | Free | Easy (recommended) |
| **WhatsApp** | Meta/Twilio pricing | Medium |
| **Email** | SMTP / mock | Already in v2 |

---

## Telegram (recommended)

### 1. Create a bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram  
2. `/newbot` → name your bot → copy the **token**  
3. Add to `backend/.env`:

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_WEBHOOK_SECRET=random-long-secret   # optional, for production webhook
```

### 2. Link your account (Career OS UI)

1. Open `/loop`  
2. Enable **Telegram alerts**  
3. Click **Generate link code**  
4. Open your bot (link shown)  
5. Send: `/link YOUR_CODE`  
6. Bot replies “Linked!”

**Production webhook** (so `/link` works without polling):

```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://YOUR_API/api/v1/loop-engineer/notify/telegram/webhook?secret=YOUR_SECRET"
```

### 3. Manual chat ID (alternative)

1. Message [@userinfobot](https://t.me/userinfobot) → copy your **Id**  
2. Paste into **Telegram chat ID** field in `/loop`  
3. Click **Test Telegram**

---

## WhatsApp

Two providers supported — set **one** in `.env`:

### Option A — Meta Cloud API (official)

1. [Meta for Developers](https://developers.facebook.com/) → WhatsApp → API Setup  
2. Get **Phone number ID** and **Access token**  
3. Add test recipient phone in Meta dashboard  

```env
WHATSAPP_PROVIDER=meta
WHATSAPP_META_ACCESS_TOKEN=EAAG...
WHATSAPP_META_PHONE_NUMBER_ID=1234567890
```

**Note:** User may need to message your business number first (24h session window) before you can send free-form text. For cold outreach use an approved [message template](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates).

### Option B — Twilio WhatsApp

1. Twilio console → Messaging → WhatsApp sandbox (dev) or approved sender (prod)  

```env
WHATSAPP_PROVIDER=twilio
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
```

### 3. Configure in Career OS

1. `/loop` → enable **WhatsApp alerts**  
2. Enter phone in **E.164** format: `+14155552671`  
3. **Test WhatsApp**

---

## What you receive

When packets are built after a scan:

```
Career OS: 3 job packet(s) ready for review

• Senior Engineer @ Stripe (match 85%)
  https://your-app/loop?packet=...

Nothing was applied — confirm in Loop Engineer when ready.
```

Tap link → review JD, company research, resume preview → **Confirm** or **Skip**.

---

## API

```
GET  /api/v1/loop-engineer/notify/channels
POST /api/v1/loop-engineer/notify/telegram/link-code
POST /api/v1/loop-engineer/notify/telegram/webhook   # Telegram → your server
POST /api/v1/loop-engineer/notify/test                 { "channel": "telegram" }
```

Schedule fields (also in `PUT /loop-engineer/schedule`):

```json
{
  "notify_email": true,
  "notify_telegram": true,
  "notify_whatsapp": false,
  "telegram_chat_id": "123456789",
  "whatsapp_phone": "+14155552671"
}
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Telegram “bot not configured” | Set `TELEGRAM_BOT_TOKEN` and restart API |
| `/link` does nothing | Register webhook URL (HTTPS required) or paste chat ID manually |
| WhatsApp Meta error 131047 | User must message business number first |
| Twilio sandbox | Join sandbox via code Twilio sends you |
| No notification but packets exist | Check Inbox digest + `/loop` — in-app always works |
