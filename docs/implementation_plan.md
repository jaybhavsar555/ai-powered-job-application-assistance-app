# AI-Powered Job Application Assistant - Implementation Plan

This document serves as the master architecture and implementation plan for the production-ready AI Job Application Assistant. It incorporates the core requirement of **human-in-the-loop** for all critical actions, the **JSON-first resume approach**, a **user knowledge base**, and a **workflow-driven CRM model**.

## User Review Required

> [!IMPORTANT]
> Please review the newly added **Section 8: Frontend AI Operating System UI/UX**. 
> We need to decide on our execution path: Should we build the **Resume JSON Library API** next (continuing with Backend CRUD), or should we immediately start scaffolding the **Frontend Workflow Canvas & Streaming Architecture** described below?

## 1. System Architecture

The system follows a modular, clean architecture.

- **Backend**: Python 3.11+, FastAPI (Async), Pydantic v2
- **Frontend**: Next.js 14+ (App Router), TypeScript, Tailwind CSS, Shadcn UI, React Flow (for canvas)
- **Database (Relational)**: PostgreSQL (using SQLAlchemy 2.0 & Alembic)
- **Database (Vector & Cache)**: Qdrant, Redis (for Celery message broker and caching)
- **Workflow Engine**: LangGraph (for stateful, checkpointed agent workflows, with streaming enabled)
- **Background Jobs**: Celery + Redis
- **Storage**: Local filesystem
- **AI Models**: OpenAI (GPT-4o), OpenAI text-embedding-3-small

---

## 2. Folder Structure

*(See existing layout, extended with React Flow components)*

---

## 3. Database Schema Overview

*(Schema remains the same, leveraging the expanded JSONB fields in UserKnowledgeBase for Achievements, Metrics, etc.)*

---

## 4. API Specification Outline

**FastAPI REST Endpoints (Standard CRUD)**
- `POST /api/v1/auth/login`
- `GET /api/v1/users/me/knowledge`
- `PUT /api/v1/users/me/knowledge`

**Workflow Endpoints (Triggers & Human-in-the-loop)**
- `POST /api/v1/jobs/extract` - Triggers Job Intake Agent
- `POST /api/v1/workflows/{job_id}/start` - Starts tailoring workflow
- `GET /api/v1/workflows/{workflow_id}/stream` - **(NEW)** SSE Endpoint streaming LangGraph tokens, state, and reasoning to the UI.
- `POST /api/v1/workflows/{workflow_id}/approve` - Submits human approval
- `POST /api/v1/workflows/{workflow_id}/reject` - Submits human rejection/feedback

---

## 5. LangGraph Workflows

The application tailoring process is modeled as a cyclic graph with strict `interrupt_before` breakpoints for human-in-the-loop validation. Nodes emit real-time status updates (e.g. `Thinking...`, `Extracting Keywords...`) that the frontend consumes.

---

## 6. Agent Interfaces

Each agent will be an isolated module with a clear input/output Pydantic schema and cost/latency tracking.

---

## 7. Execution Plan (Module by Module)

* **Phase 1-5**: Setup, Database, SaaS Foundation, Knowledge Base **(COMPLETED)**
* **Phase 6**: Resume JSON Library API (Backend CRUD)
* **Phase 7**: Job Intake Agent (URL scraping, PDF parsing, Normalization)
* **Phase 8**: LangGraph Integration & SSE Streaming infrastructure
* **Phase 9**: Frontend "AI OS" UI (Workflow Canvas, Timeline View, Agent Inspector)
* **Phase 10**: ATS & Resume Optimization Agents
* **Phase 11**: Document Generation, Company Research, Outreach Agents

---

## 8. Frontend AI Operating System UI/UX (NEW)

To differentiate the product, the UI will act as a transparent "AI Operating System" rather than a black-box spinner. It borrows concepts from LangGraph Studio, Linear, and NotebookLM:

1. **Workflow Canvas**: A read-only node graph (using `reactflow`) visualizing the pipeline (Job Intake -> Research -> ATS -> Optimize -> Approval). Nodes update in real-time.
2. **Timeline View & Live Streaming**: An event timeline showing exact timestamps of agent actions, driven by Server-Sent Events (SSE) from the FastAPI backend.
3. **Agent Inspector**: Clicking a node opens a side-panel revealing:
   - Model used, execution time, token count, cost.
   - Files and Knowledge Base nodes referenced.
   - An audit trail of explicit actions taken (not just raw reasoning).
4. **NotebookLM-Style Sources**: AI suggestions (e.g., "Missing Docker") provide clickable citations opening a split-pane view highlighting exactly where in the Job Description or Knowledge Base the evidence was found.
5. **Human Approval Panel**: Distinct breakpoints where the user sees a diff (Added, Removed, Modified) and can Approve, Reject, Edit, or Ask AI Again. 
6. **Default Experience**: The default view is a clean, guided Timeline. The Canvas/Agent Inspector are togglable for advanced users to avoid overwhelming beginners.
