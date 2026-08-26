# Obsidian second brain (Jay OS)

**This is separate from Knowledge Vault** (`/vault` in the app). Knowledge Vault stays in Postgres + Qdrant for skills, job portals, and semantic search. Obsidian Second Brain writes Markdown to your local Jay OS folder. Use both.

Career OS can sync applications, interview prep, and daily learning notes into your local Obsidian vault — for example:

`C:\Users\Asus\OneDrive\Desktop\Jay OS`

## One-time setup (Windows)

1. Open `backend/.env` and set:

```env
OBSIDIAN_VAULT_PATH=C:\Users\Asus\OneDrive\Desktop\Jay OS
OBSIDIAN_SYNC_ON_STAGE_CHANGE=true
```

2. If you run the API in Docker, mount the vault into the container. In `docker-compose.yml` under `api`:

```yaml
volumes:
  - ./backend:/app
  - ./data/resumes:/data/resumes
  - ./data/packages:/data/packages
  - "C:/Users/Asus/OneDrive/Desktop/Jay OS:/data/obsidian"
environment:
  OBSIDIAN_VAULT_PATH: /data/obsidian
```

3. Restart the API, open **Second Brain** in the UI (`/second-brain`), click **Create Career OS folders**, then **Sync all applications**.

## What gets written

```text
Jay OS/
  Career OS/
    Dashboard.md
    Applications/          # one note per job (JD + resume + ATS + stage + My notes)
    Interview Prep/        # when stage is Shortlisted or Interview
    Daily/YYYY-MM-DD.md    # daily fundamentals + code practice
    Learning/Topics/
    Learning/Practice/
    MOCs/
    Templates/
```

Your **My notes** section is preserved across re-syncs so you can keep journaling in Obsidian.

## Daily loop

1. Sync applications after tailor/apply.
2. Drag Tracker cards to **Shortlisted** → open **Prep Guide** → generate drills → sync again.
3. Click **Write today’s session** on Second Brain (or `POST /api/v1/obsidian/daily-learning`) and spend 30–45 minutes on the plan in Obsidian.
