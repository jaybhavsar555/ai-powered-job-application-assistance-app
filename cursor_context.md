# Project Context for Cursor
**Project Name**: AI Powered Job Application Assistance App (AI OS Platform)

This document contains the complete context of our conversation and the architecture of the platform we've been building. You can use this as your primary context file in Cursor to continue development seamlessly.

## Product Vision
We shifted from a standard backend-heavy application to a **Platform** with AI observability, human-in-the-loop, knowledge graph, and agent visualization built in from day one. It looks and feels like a premium AI Operating System (Obsidian/Linear dark mode aesthetic).

## Tech Stack
- **Frontend**: Next.js (App Router), Tailwind CSS, Zustand (Global State), React Flow (Agent Visualization), Server-Sent Events (SSE).
- **Backend**: FastAPI, PostgreSQL (SQLAlchemy), Redis (Pub/Sub Event Bus), LangGraph (Agent Orchestration), Langchain.
- **Architecture**: Event-driven architecture with an Agent Registry, Prompt Registry, and centralized telemetry.

## Database & Knowledge Graph Architecture
We redesigned the database to support a "Knowledge Vault" rather than static tables.
- **WikiEntity**: Extracted skills, experiences, projects, and companies are stored as graph nodes (`DBWikiEntity`) belonging to the user.
- **AgentEventLog**: Every agent execution saves exact tokens, latency, cost, and extracted evidence to PostgreSQL.
- **Core Models**: `User`, `Job`, `Application` (tracks pipeline stage), `Resume`, `ResumeVersion`, `CoverLetter`.

## Agent Workflow & Telemetry Pipeline
1. **LangGraph (`app/workflows/graph.py`)**: Orchestrates agents (Job Intake -> Company Research -> ATS Analyzer -> Resume Optimizer -> Cover Letter Agent).
2. **Base OSAgent (`app/application/agents/base.py`)**: All agents inherit from this. It automatically calculates token usage, latency, and cost, then publishes `AGENT_STARTED` and `AGENT_SUCCESS` events to a Redis Pub/Sub channel (`workflow_events`).
3. **SSE Stream (`app/api/v1/endpoints/workflows.py`)**: FastAPI subscribes to Redis and streams these events in real-time to the frontend.
4. **Zustand State (`frontend/src/hooks/useWorkflowStore.ts`)**: The frontend catches these events, updates the global state, and instantly renders the telemetry on the React Flow Canvas (`WorkflowCanvas.tsx`) and the Node Inspector (`InspectorPanel.tsx`).

## Completed Phases (0 to 7)
- **Phase 0 & 1**: Architected the system, scaffolded the Next.js `(workspace)` routes, and built the sleek dark-mode `WorkspaceLayout`.
- **Phase 2**: Built premium UI components (`ApprovalCard` for Git-diffs, `TelemetryBadge`, `CustomWorkflowNode`).
- **Phase 3**: Refactored the DB schema, dropping `UserKnowledgeBase` in favor of the `WikiEntity` graph approach, and applied Alembic migrations.
- **Phase 4**: Implemented the `AgentRegistry` and refactored all backend agents to inherit from the `OSAgent` base class for unified logging.
- **Phase 5 & 6**: Built the Redis Event Bus, wired up the FastAPI SSE endpoint, and updated the React frontend to display live agent executions, animations, and exact telemetry/evidence in the Inspector panel.
- **Phase 7**: Built the Human-in-the-Loop **Approvals UI** (using the Git-diff `ApprovalCard` to accept/reject AI-generated resumes/cover letters) and the **Knowledge Vault UI** (fetching `WikiEntity` data from the DB).

## Phase 8 (In Progress / Partially Complete)
1. **Jobs Tracker (`/tracker`)** — **DONE**: Kanban board over `DBApplication` stages (Wishlist → Researching → Ready → Applied → Interview → Rejected). Backend: `GET/POST /applications`, `PATCH /applications/{id}/stage`. Job ingest auto-creates a Wishlist application. Frontend: drag-and-drop `KanbanBoard` with optimistic stage updates.
2. **Analytics/Dashboard (`/analytics`)**: Still a placeholder — needs to aggregate telemetry (costs, tokens, success rates) from `AgentEventLog`.
3. **Long-Term Memory / Vector DB**: We have `vector_id` in our `WikiEntity` table, but Qdrant/Pinecone integration for semantic retrieval is pending.

You are now fully caught up. Happy coding in Cursor!
