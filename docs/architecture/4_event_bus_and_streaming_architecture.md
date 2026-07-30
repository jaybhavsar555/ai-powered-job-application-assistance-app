# Event Bus & Streaming Pipeline Architecture

Frontend transparency requires live agent telemetry. Career OS uses **Redis Pub/Sub + FastAPI SSE** (implemented).

## 1. Requirements
On “Start Workflow”, the UI must learn:
1. Active agent  
2. Success / error  
3. Tokens, latency, estimated cost  
4. Evidence payload  
5. Final state for Approvals  

## 2. Redis Event Bus (implemented)

- Module: `infrastructure/events/bus.py`  
- Channel used today: **`workflow_events`** (shared; filter by `application_id` / `job_id` in the SSE loop)

### Event types (practical schema)

```json
{
  "type": "AGENT_STARTED | AGENT_SUCCESS | AGENT_ERROR | COMPLETED | ERROR",
  "node": "ats_analyzer",
  "application_id": "uuid-or-job-id",
  "latency_ms": 1200,
  "tokens": 165,
  "cost": 0.0012,
  "evidence": {},
  "final_state": {},
  "error": "optional"
}
```

`OSAgent.execute` publishes STARTED / SUCCESS / ERROR and persists SUCCESS & ERROR rows to `agent_event_logs`.

## 3. FastAPI SSE (implemented)

- Endpoint: `GET /api/v1/workflows/{job_id}/stream`  
- Starts LangGraph in a background task  
- Subscribes to Redis and yields `data: {json}\n\n` until COMPLETED / ERROR  

Frontend: `useWorkflowStream` → `useWorkflowStore` → Canvas nodes + Inspector + Terminal.

## 4. Analytics consumer

The same Postgres logs feed `GET /analytics/summary` (tokens, cost heuristic, success rate, per-agent breakdown, recent events).

## 5. Future refinements
- Per-application Redis channels (`workflow.events.{id}`) for multi-tenant scale  
- Token-level LLM streaming events  
- Checkpointed LangGraph persistence keyed by application  
