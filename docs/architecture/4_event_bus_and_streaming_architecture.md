# Event Bus & Streaming Pipeline Architecture

To achieve the "AI Workspace" transparency requirements, the frontend must receive live telemetry from the backend agents. Standard HTTP requests are insufficient because they block until the entire LLM chain completes. We must move to an Event-Driven Architecture.

## 1. The Core Problem
When the user clicks "Start Workflow", multiple agents execute sequentially or in parallel. The UI needs to know:
1. Which agent is currently active?
2. What text is the agent currently generating (streaming)?
3. Did the agent encounter an error?
4. How many tokens did the agent consume?
5. What was the exact latency of the call?

## 2. Event Bus Implementation (Redis Pub/Sub)

We will use Redis as the backbone for our Event Bus. 

### Event Topics
- `workflow.events.{application_id}`: High-level state changes (e.g., "ATS Agent Started").
- `workflow.stream.{application_id}`: Low-level LLM token streams.
- `workflow.metrics.{application_id}`: Cost, token, and latency telemetry.

### Event Schema
Every event emitted onto the bus will follow this standard schema:

```json
{
  "event_id": "uuid",
  "timestamp": "2026-07-30T12:00:00Z",
  "application_id": "uuid",
  "agent_name": "CoverLetterAgent",
  "event_type": "LLM_TOKEN_STREAM",
  "payload": {
    "chunk": "Based on my research..."
  }
}
```

## 3. The FastAPI Streaming Layer (SSE)

The Next.js client does not connect directly to Redis. Instead, it connects to a FastAPI Server-Sent Events (SSE) endpoint.

1. **Client Connection**: Next.js opens an `EventSource` connection to `/api/v1/applications/{id}/stream`.
2. **Backend Subscription**: FastAPI subscribes to the Redis topic `workflow.*.{application_id}` using `asyncio` and `aioredis`.
3. **Data Relay**: As Redis receives events from the Celery workers or LangGraph nodes, FastAPI yields those events directly into the HTTP stream.

## 4. LangGraph Observability Hook

To avoid littering our agent code with `emit()` statements, we will build a custom LangGraph callback handler. 

This handler will automatically hook into LangChain's underlying LLM calls and automatically broadcast events to the Redis bus when:
- `on_llm_start`: Emits "Agent Thinking..." to the UI.
- `on_llm_new_token`: Emits raw text for typewriter effects in the Live Log.
- `on_llm_end`: Emits Token Usage and Cost metrics.

## 5. Security & Authentication

Because the SSE stream exposes raw LLM thought processes and potentially sensitive user data (resumes, API keys), the stream endpoint must be tightly secured.
- The `/stream` route will require a valid JWT token.
- The application ID being streamed must belong to the authenticated `user_id`.
