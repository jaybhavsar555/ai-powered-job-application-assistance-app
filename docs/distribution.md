# Distributing Career OS (self-host on each user's machine)

**Goal:** other people run Career OS on **their** PC/server. Your laptop stays offline and uninvolved.

```text
                    YOUR IMAGES / REPO
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           User A        User B       User C
              │            │            │
           Docker        Docker       Docker
         (their PC)   (their PC)   (their PC)
```

This is **Option A / C** from the product decision: downloadable Compose stack — not a public URL hosted on your machine.

---

## What end users need

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or [Docker Engine + Compose](https://docs.docker.com/engine/install/) (Linux)
2. This repo **or** your published images + `docker-compose.dist.yml` + `.env.dist.example`
3. Disk for Ollama models (~2 GB for `qwen2.5:3b`) — **models are pulled at setup time, not baked into the API image**

They do **not** need Node, Python, Playwright, or TeX.

---

## End-user install (recommended)

```bash
git clone <YOUR_REPO_URL> career-os
cd career-os
cp .env.dist.example .env.dist
# edit SECRET_KEY, POSTGRES_PASSWORD, REDIS_PASSWORD
```

**macOS / Linux:**

```bash
chmod +x scripts/dist-setup.sh
./scripts/dist-setup.sh
```

**Windows (PowerShell):**

```powershell
.\scripts\dist-setup.ps1
```

Then open **http://localhost:3000** → Register at `/login`.

Stop:

```bash
docker compose -f docker-compose.dist.yml --env-file .env.dist down
```

Data (Postgres, Qdrant, Ollama models) stays in Docker volumes until you `docker compose … down -v`.

---

## Maintainer: publish images (Docker Hub)

1. Create a Hub account and repos (e.g. `career-os-api`, `career-os-web`):  
   [Create a repository](https://docs.docker.com/docker-hub/repos/create/)
2. `docker login`
3. Build & push ([push docs](https://docs.docker.com/docker-hub/repos/manage/hub-images/push/)):

```bash
export DOCKERHUB_USER=youruser
export TAG=1.0.0
chmod +x scripts/dist-publish.sh
./scripts/dist-publish.sh
```

4. Tell users to add to `.env.dist`:

```env
API_IMAGE=youruser/career-os-api:1.0.0
WEB_IMAGE=youruser/career-os-web:1.0.0
```

Then `docker compose -f docker-compose.dist.yml --env-file .env.dist pull`  
([compose pull](https://docs.docker.com/reference/cli/docker/compose/pull/)) and run `dist-setup`.

Without Hub, users who clone the repo still work: Compose **builds** from `./backend` and `./frontend` on first start.

---

## Offline handoff (Option B — `.tar`)

Large files; skip unless the recipient has no Hub access:

```bash
docker save youruser/career-os-api:1.0.0 youruser/career-os-web:1.0.0 -o career-os-images.tar
```

Receiver:

```bash
docker load -i career-os-images.tar
# set API_IMAGE / WEB_IMAGE in .env.dist to those tags
./scripts/dist-setup.sh
```

Do **not** pack the Ollama volume into the tar — have them `ollama pull` (setup script already does this).

---

## Security rules

| Do | Don't |
|----|--------|
| Put secrets only in `.env.dist` (gitignored) | Bake `SECRET_KEY` / API keys into Dockerfile `ENV` |
| Ship `.env.dist.example` with placeholders | Commit real `.env.dist` or `.env.production` |
| Let each user register their own account | Share one JWT / admin password across clients |
| Keep `ALLOW_DEMO_AUTH=false` on shared demos | Expose Postgres/Redis ports publicly without a firewall |

Inspectable images must remain secret-free.

---

## Dev vs distribute

| File | Audience |
|------|----------|
| `docker-compose.yml` | **You** developing: API hot-reload, frontend via `npm run dev` |
| `docker-compose.dist.yml` | **Anyone**: API + web + db + redis + qdrant + ollama, one installer |
| `docker-compose.prod.yml` | Hardened prod / VPS (same idea as dist) |

Later, the **same** dist/prod Compose can move to a cheap VPS when you want a public URL — that is a different product (“visit a link”) and needs hosting money.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Setup refuses to start | Replace `change-me` / `replace-with` values in `.env.dist` |
| Agents fail | Wait for `ollama pull` to finish; check `docker compose … logs ollama` |
| UI loads, API CORS errors | `CORS_ORIGINS` and `NEXT_PUBLIC_API_URL` must match host ports |
| Out of disk | Models live in `ollama_data` volume; remove unused tags with `ollama rm` |

---

## Docker Hub / GHCR (optional — deferred)

**Do not publish Hub images until daily use and interview conversion prove the stack.**  
Until then: end users `git clone` + `docker compose -f docker-compose.dist.yml build` (or `scripts/dist-setup.*`).

When ready later, see `scripts/dist-publish.sh` and set `API_IMAGE` / `WEB_IMAGE` in `.env.dist`.

Optional secrets in `.env.dist` (from `.env.dist.example`):

- `HUNTER_API_KEY` — recruiter email finder  
- `SMTP_*` — real send with resume PDF attached (otherwise Outreach: Download PDF & Gmail + copy package folder)  
- `JOB_DISCOVERY_*` — Remotive/RemoteOK/Arbeitnow + Vault, max 15 results  
