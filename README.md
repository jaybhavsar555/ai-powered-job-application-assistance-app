# AI Powered Job Application Assistant (Career OS)

Local-first **AI operating system** for job search: discover roles, tailor resumes, build apply packages, Review & Apply with a Chrome extension, draft outreach, and follow up — with human gates (not silent mass-apply).

| Layer | Runs where | Tech |
|-------|------------|------|
| **Backend + data + LLM** | **Docker always** (Python deps installed in the image) | FastAPI, LangGraph, Postgres, Redis, Qdrant, Ollama |
| **Frontend** | **Your machine** (`npm install` / `npm run dev`) | Next.js, Tailwind, Zustand |
| **Optional** | Browser | Chrome/Edge extension for form fill |

API: **http://localhost:8001** · UI: **http://localhost:3000** (or **3001** if 3000 is taken)

---

## Share with others (self-host — recommended)

Do **not** expose your laptop. Each person runs the stack on **their** machine:

```text
GitHub / Docker Hub  →  docker compose  →  their PC (API + DB + Redis + Qdrant + Ollama + Web)
```

**End user (Windows / macOS / Linux) — Docker only, no Node required:**

```bash
git clone <YOUR_REPO_URL> career-os && cd career-os
cp .env.dist.example .env.dist   # edit SECRET_KEY + DB/Redis passwords
./scripts/dist-setup.sh          # Windows: .\scripts\dist-setup.ps1
```

Open **http://localhost:3000** → Register.

Ollama **models are pulled during setup** (not baked into the API image). Full guide: [docs/distribution.md](docs/distribution.md) (Docker Hub publish, offline `.tar`, security).

| Mode | Command | Frontend |
|------|---------|----------|
| **Distribute / demo** | `scripts/dist-setup.*` + `docker-compose.dist.yml` | Inside Docker |
| **Daily develop (this README below)** | `docker compose up -d` + `npm run dev` | Host Node |

---

## Who this is for (use cases)

| Use case | How Career OS helps |
|----------|---------------------|
| **Daily apply loop** | Inbox → wishlist → Canvas tailor → Approvals → package → Review & Apply → outreach → follow-up |
| **Quality over volume** | ATS-aware resume + cover letter + screening Q&A bank; you (or gated Auto) submit on the real site |
| **Local / free LLM** | Default **Ollama** in Docker — no OpenAI credits required |
| **Cloud LLM** | Optional OpenAI key via Canvas LLM switch (needs billing credits) |
| **Team / roommate setup** | Same repo: each person registers their own account at `/login` |

**Not** a “applies while you sleep” LinkedIn bot. Positioning: *Review & Apply + tailored packages*.

---

## Prerequisites

Install these on your computer before setup:

| Tool | Why | Download / install |
|------|-----|--------------------|
| **Docker Desktop** (Windows / macOS) or **Docker Engine + Compose** (Linux) | Runs API, Postgres, Redis, Qdrant, Ollama | [Docker Desktop](https://www.docker.com/products/docker-desktop/) · [Linux install](https://docs.docker.com/engine/install/) · [Compose plugin](https://docs.docker.com/compose/install/) |
| **Node.js 20+** (LTS) | Frontend only | [nodejs.org](https://nodejs.org/) · or [fnm](https://github.com/Schniz/fnm) / nvm |
| **Git** | Clone the repo | [git-scm.com](https://git-scm.com/downloads) |

Optional:

- **NVIDIA GPU + [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)** — faster Ollama (use `docker-compose.gpu.yml`)
- **Google Chrome or Edge** — for the autofill extension (`extension/`)

You do **not** need a local Python venv, Playwright, or TeX on the host — those are inside the API Docker image.

### Confirm Docker works

**Windows (PowerShell)** / **macOS (Terminal)** / **Linux (bash)**:

```bash
docker --version
docker compose version
```

If either command fails, install Docker from the links above, start Docker Desktop, and retry.

---

## First-time setup (all OS)

Commands below work in **PowerShell**, **macOS Terminal**, and **Linux bash** unless noted.

### 1. Clone and enter the repo

```bash
git clone <YOUR_REPO_URL> ai_powered_job_application_assistance_app
cd ai_powered_job_application_assistance_app
```

### 2. Create env files

**Windows (PowerShell):**

```powershell
Copy-Item backend\.env.example backend\.env
Copy-Item frontend\.env.example frontend\.env.local
```

**macOS / Linux:**

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

Edit `backend/.env`:

- Set a long random `SECRET_KEY` (do not leave the example in shared/prod use)
- Optional: `OPENAI_API_KEY` if you want cloud LLM later
- Leave SMTP empty to use copy/mailto for outreach (fine for personal use)

Frontend default `NEXT_PUBLIC_API_URL=/api/v1` proxies through Next.js to Docker on port **8001** — usually no change needed.

### 3. Add your resumes (optional but recommended)

Put base resume files (PDF / DOCX / Markdown) in:

```text
data/resumes/
```

Tailored packages will appear under `data/packages/` after Approvals.

### 4. Start the backend stack in Docker (always-on)

```bash
docker compose up -d --build
```

First build can take several minutes (Python deps + Playwright Chromium + TeXLive inside the image).

Pull the local chat model (required for real agent output — **mock LLM is disabled** by default):

```bash
docker compose exec ollama ollama pull qwen2.5:3b
```

**With NVIDIA GPU** (Linux/Windows + toolkit only):

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
docker compose exec ollama ollama pull qwen2.5:3b
```

Check API health:

```bash
curl http://127.0.0.1:8001/api/v1/health
```

Windows PowerShell alternative:

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8001/api/v1/health | Select-Object -ExpandProperty Content
```

Open API docs: [http://localhost:8001/docs](http://localhost:8001/docs)

Services (host ports):

| Service | Port |
|---------|------|
| API (FastAPI) | **8001** |
| Postgres | 5432 |
| Redis | 6379 |
| Qdrant | 6333 |
| Ollama | 11434 |

Containers use `restart: unless-stopped` so they come back after reboot while Docker is running.

### 5. Run the frontend locally

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

If port **3000** is already used:

```bash
npm run dev -- -p 3001
```

Then open [http://localhost:3001](http://localhost:3001).

### 6. Create your account

1. Go to **/login**
2. **Register** with your email + password (recommended for your own jobs), or use a seeded demo account if `SEED_DEV_USERS=true`:

| Email | Password | Role |
|-------|----------|------|
| `demo@example.com` | `Demo1234!` | Demo |
| `admin@example.com` | `Admin123!` | Admin |
| `user@example.com` | `User1234!` | User |

Each account has its own wishlist and packages — register your own for real job hunting.

---

## Daily use (after setup)

**Terminal 1 — backend already in Docker** (start if stopped):

```bash
docker compose up -d
```

**Terminal 2 — frontend:**

```bash
cd frontend
npm run dev
```

Recommended loop:

1. **/jobs** or **/discovery** — import a JD (paste full text if URL scrape fails)
2. **/canvas** — pick that Tracker job · LLM = **Ollama** · **Simulate**
3. **/approvals** — accept resume + cover
4. **/resumes** or package download — DOCX/PDF under `data/packages/`
5. **/apply** + optional Chrome extension — Review & Apply on the real site
6. **/outreach** — add recruiter contact manually if email is empty · send via mailto/SMTP
7. Mark **Applied** → follow-up draft appears in **/inbox** after ~3 days

Canvas **Mock** LLM and demo jobs are **disabled** so failures (no model, bad scrape, missing JD) stay visible.

---

## OS-specific notes

### Windows

- Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) (WSL2 backend recommended)
- Use **PowerShell** or **Windows Terminal** in the repo root
- Keep Docker Desktop **running** before `docker compose up`
- If `npm` is missing, install [Node.js LTS](https://nodejs.org/) and reopen the terminal

### macOS

- Install [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
- Apple Silicon is fine; Ollama runs on CPU in default compose (GPU overlay is NVIDIA-only)
- Use Terminal or iTerm; same `docker compose` / `npm` commands as Linux

### Linux

- Install [Docker Engine](https://docs.docker.com/engine/install/) + [Compose plugin](https://docs.docker.com/compose/install/)
- Add your user to the `docker` group (then log out/in): `sudo usermod -aG docker $USER`
- NVIDIA: install toolkit, then use `docker-compose.gpu.yml` as shown above

---

## Useful Docker commands

```bash
# Status
docker compose ps

# API logs
docker compose logs -f api

# Rebuild API after requirements.txt / Dockerfile changes
docker compose up -d --build api

# Shell inside API container
docker compose exec api bash

# Stop stack (data volumes kept)
docker compose stop

# Stop and remove containers (volumes kept)
docker compose down
```

Python packages are **only** in the image — do not run `pip install` on the host for normal use. See [docs/docker_backend.md](docs/docker_backend.md).

---

## Workspace routes

| Route | Purpose |
|-------|---------|
| `/inbox` | Next actions, 48h jobs, follow-ups |
| `/jobs` | Wishlist · import URL/JD |
| `/quick-apply` | Paste LinkedIn hiring post → tailor resume → draft email + download package |
| `/discovery` | Prefs → remote board matches |
| `/canvas` | LangGraph agents · job picker · LLM switch |
| `/approvals` | HITL resume / cover |
| `/resumes` | Resume Studio · packages |
| `/apply` | Review & Apply session |
| `/screening-qa` | Answers for extension autofill |
| `/tracker` | Kanban stages |
| `/outreach` | Cold email / follow-up drafts |
| `/vault` | Knowledge entities + search |
| `/login` | Register / sign in |

---

## Optional: Chrome extension

See [extension/README.md](extension/README.md) for load-unpacked install, API base URL, and Review vs gated Auto Apply (LinkedIn blocked by default).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `docker` not found | Install/start [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Engine |
| API won’t start | `docker compose logs api` · ensure `backend/.env` exists |
| Agents fail / LLM errors | `docker compose exec ollama ollama pull qwen2.5:3b` · Canvas → **Ollama** |
| OpenAI “Connection error” | Usually no credits — use Ollama instead |
| Job import empty | Paste full JD into `description_raw` — scrapes do not invent text |
| Frontend can’t reach API | Docker API on **8001** · `NEXT_PUBLIC_API_URL=/api/v1` · CORS includes 3000/3001 |
| Port 3000 in use | `npm run dev -- -p 3001` |
| Empty recruiter email | Expected until you add a contact manually (lookup not configured) |

More help: [docs/walkthrough.md](docs/walkthrough.md) · [docs/user_guide.md](docs/user_guide.md)

---

## CI / production / distribute

- CI: `.github/workflows/ci.yml` — frontend lint/build, backend pytest (`LLM_FORCE_MOCK`), Docker image build
- **Give others a copy (self-host):** [docs/distribution.md](docs/distribution.md) · `docker-compose.dist.yml` · `scripts/dist-setup.*`
- Production / VPS: [docs/deploy.md](docs/deploy.md)

---

## Repo layout

```text
backend/                   FastAPI + agents (Docker image)
frontend/                  Next.js (host npm OR dist web image)
extension/                 Chrome/Edge autofill
data/resumes/              Base resumes (bind-mounted)
data/packages/             Generated packages
scripts/dist-setup.*       One-shot installer for end users
scripts/dist-publish.sh    Push API/web images to Docker Hub
docs/                      Guides & architecture
docker-compose.yml         Dev: API in Docker, UI on host
docker-compose.dist.yml    Distribute: full stack on one machine
docker-compose.gpu.yml     Optional NVIDIA for Ollama (dev)
```

---

## More documentation

- [**Distribute / self-host**](docs/distribution.md) — Docker Hub, offline tar, installer
- [**User guide**](docs/user_guide.md) — features and real apply loop
- [**Docker backend**](docs/docker_backend.md) — why no host venv
- [Walkthrough](docs/walkthrough.md) — verify steps & troubleshooting
- [Competitor / Review & Apply research](docs/competitor_auto_apply_research.md)
- [Architecture](docs/architecture_design.md)
- [Deploy](docs/deploy.md)
