import json
import asyncio
from typing import AsyncGenerator
from app.workflows.graph import app_graph
from app.infrastructure.events.bus import event_bus

class WorkflowService:
    async def stream_workflow(self, job_id: str, user_id: str) -> AsyncGenerator[str, None]:
        # Initial State
        initial_state = {
            "job_id": job_id,
            "user_id": user_id,
            "resume_id": None,
            "messages": [],
            "job_details": {},
            "company_research": {},
            "ats_score": None,
            "tailored_resume": {},
            "requires_human_approval": False
        }

        # Background task to run the graph
        async def run_graph():
            try:
                final_state = initial_state
                # We can also pass application_id here if we want the graph to pass it to agents
                async for chunk in app_graph.astream(initial_state):
                    # chunk is a dict of {node_name: {state_updates}}
                    for node_name, state_updates in chunk.items():
                        final_state.update(state_updates)
                        
                await event_bus.publish("workflow_events", {
                    "type": "COMPLETED", 
                    "application_id": job_id,
                    "final_state": final_state
                })
            except Exception as e:
                await event_bus.publish("workflow_events", {"type": "ERROR", "error": str(e), "application_id": job_id})
                
        asyncio.create_task(run_graph())

        # Stream events from Redis
        try:
            async for event in event_bus.subscribe("workflow_events"):
                # Filter by application_id (using job_id as a proxy for now)
                if event.get("application_id") == job_id or not event.get("application_id"):
                    yield f"data: {json.dumps(event)}\n\n"
                    
                    if event.get("type") in ["COMPLETED", "ERROR"]:
                        break
        except asyncio.CancelledError:
            pass
