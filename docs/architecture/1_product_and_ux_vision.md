# Product Requirements Document (PRD) & UX Vision

## 1. Product Vision
The product is evolving from a simple point-and-click "Resume Updater" into a comprehensive **Career Operating System**. It acts as a permanent, persistent Knowledge Vault that learns about the user over time, tracking applications not as simple records, but as long-term engineering projects.

### Core Principles
1. **AI Observability**: The user must never wonder *what* the AI is doing. Every agent action, API call, and reasoning step must be exposed visually.
2. **Human-in-the-Loop**: The AI drafts, the Human approves. No emails are sent, no resumes are finalized without an explicit Git-style diff approval.
3. **Knowledge Accumulation**: Nothing is a one-off. Every job description parsed, every interview note recorded, and every skill analyzed is permanently stored in the Knowledge Graph for future context.

## 2. Information Architecture
The platform shifts away from a standard CRM dashboard and embraces a workspace model akin to Obsidian or Linear.

### Top-Level Workspaces
- **AI Workspace**: The central hub for visual agent execution (Workflow Canvas, Agent Timeline, Live Logs).
- **Knowledge Vault**: The persistent data layer (Raw ingestion, Wiki profiles, Questions/Gaps, Digests).
- **Application Tracker**: The Linear-style board managing individual application lifecycles as projects.
- **Approval Center**: A unified inbox for pending AI actions requiring human sign-off.

## 3. UX Flow & User Journey

### The Intake Journey
1. **Trigger**: User pastes a Job URL or uses the upcoming browser extension.
2. **Animation**: The UI transitions to the AI Workspace.
3. **Visual Execution**: The React Flow canvas animates. The Job Intake Agent node lights up, extracts HTML via Playwright, and emits structured JSON.
4. **Knowledge Sync**: The extracted data is cross-referenced with the Knowledge Vault to immediately identify skill gaps.

### The Approval Journey (Git-Diff UX)
1. **Drafting**: The Resume Optimizer Agent suggests changes to bullet points based on the job context.
2. **Notification**: The Approval Center lights up.
3. **Diff View**: The user sees the old bullet point in red, the new bullet point in green, and an "Evidence Panel" explaining exactly *why* the ATS Analyzer recommended this change.
4. **Action**: User clicks "Approve", "Reject", or "Edit".

## 4. Conceptual Wireframes

### AI Workspace Wireframe
```text
+-------------------------------------------------------------+
| [ Sidebar ]   |  Workflow Canvas (React Flow)               |
| - Vault       |                                             |
| - Apps        |     [ Job Intake ] -> [ ATS Analyzer ]      |
| - Approval    |            |                                |
| - Settings    |     [ Knowledge Sync ]                      |
|               |                                             |
|               +---------------------------------------------+
|               |  Agent Timeline & Live Logs                 |
|               |  > ATS Analyzer: Checking JD for Python     |
|               |  > ATS Analyzer: Missing 'FastAPI' skill    |
+-------------------------------------------------------------+
```

### Git-Diff Approval Wireframe
```text
+-------------------------------------------------------------+
|  Review Resume Optimization  [ Approve ] [ Reject ]         |
+-------------------------------------------------------------+
|  Old (Current Resume)                                       |
|  - Built an API using Python and SQL for users.             |
+-------------------------------------------------------------+
|  New (Optimized for Job ID: 9812)                           |
|  + Designed a high-throughput FastAPI service in Python,    |
|    backed by PostgreSQL, improving response time by 40%.    |
+-------------------------------------------------------------+
|  Evidence Panel:                                            |
|  * The Job Description specifically requested 'FastAPI'.    |
|  * The Knowledge Vault knows you used Postgres on this      |
|    project (from Project notes ID: 12).                     |
+-------------------------------------------------------------+
```
