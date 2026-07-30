# AI Powered Job Application Assistant

A production-grade, local-first "AI Operating System" for automating job applications.
This project orchestrates multiple specialized LLM agents (Job Scraper, ATS Analyzer, Resume Optimizer, Cover Letter Writer) into a stateful, event-driven pipeline using **LangGraph**. It features a modern, real-time visual canvas built with **Next.js**, **Tailwind**, and **React Flow**.

## Architecture Stack

- **Frontend**: Next.js (App Router), React Flow, TailwindCSS, Lucide Icons.
- **Backend API**: FastAPI, Python 3.11, Clean Architecture (Domain-Driven Design).
- **AI Orchestration**: LangGraph, Instructor (Structured JSON enforcement), OpenAI.
- **Databases (Hybrid)**: PostgreSQL (Relational schema via SQLAlchemy) + JSONB columns for dynamic knowledge bases. Redis for Celery queues. Qdrant for Vector search.
- **Infrastructure**: Docker Compose + GitHub Actions CI.

---

## Quick Start

### 1. Start Databases
Ensure Docker is running, then spin up Postgres, Redis, and Qdrant:
```bash
docker-compose up -d
```

### 2. Configure environment
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# Edit backend/.env and set OPENAI_API_KEY and SECRET_KEY
```

### 3. Start the Backend API (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
*API Docs available at: `http://localhost:8000/docs`*

### 4. Start the Frontend OS (Next.js)
```bash
cd frontend
npm install
npm run dev
```
*UI available at: `http://localhost:3000/canvas`*

---

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on every push and PR to `main`:

| Job | Checks |
|-----|--------|
| Frontend | `npm ci`, lint, production build |
| Backend | install deps, import smoke test, pytest |
| Docker | builds the backend image |

---

## The Agent Pipeline

This application leverages a multi-agent **LangGraph** architecture. Instead of one massive prompt, the system relies on specialized, single-purpose agents:
1. **Job Intake Agent**: Normalizes raw job descriptions.
2. **Company Research Agent**: Pulls tech stack and culture data.
3. **ATS Analyzer**: Compares the user's base resume against the JD to find exact missing keywords.
4. **Resume Optimizer**: Weaves missing keywords into factually accurate resume bullets.
5. **Cover Letter Agent**: Drafts highly personalized letters using specific "hooks".

All agents communicate via a shared `AgentState` and emit real-time events via **Server-Sent Events (SSE)** to the frontend React Flow canvas.

## Folder Structure
- `/backend`: The FastAPI application, Domain models, LangGraph workflows, and Agent classes.
- `/frontend`: The Next.js dashboard, React Flow canvas, and Timeline UI.
- `/docs`: Markdown design docs, walkthroughs, and architecture rules.
