import json
import asyncio
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import UUID

from sqlalchemy.future import select

from app.workflows.graph import get_app_graph, thread_config
from app.infrastructure.events.bus import event_bus
from app.infrastructure.db.session import async_session
from app.infrastructure.db.models import DBApplication

CHANNEL = "workflow_events"


class WorkflowService:
    @property
    def app_graph(self):
        return get_app_graph()

    async def _persist_checkpoint_meta(
        self, job_id: str, user_id: str, final_state: Dict[str, Any], *, status: str
    ) -> None:
        """Best-effort: stash last workflow snapshot on the related application row."""
        try:
            jid = UUID(job_id)
            uid = UUID(user_id)
        except (ValueError, TypeError):
            return
        try:
            async with async_session() as session:
                result = await session.execute(
                    select(DBApplication).where(
                        DBApplication.job_id == jid,
                        DBApplication.user_id == uid,
                    )
                )
                app = result.scalars().first()
                if not app:
                    return
                state = dict(app.workflow_state or {})
                state["checkpoint"] = {
                    "status": status,
                    "thread_id": job_id,
                    "final_state": {
                        k: v
                        for k, v in final_state.items()
                        if k
                        in (
                            "job_details",
                            "company_research",
                            "ats_score",
                            "missing_skills",
                            "tailored_resume",
                            "cover_letter",
                            "requires_human_approval",
                            "messages",
                        )
                    },
                }
                app.workflow_state = state
                await session.commit()
        except Exception:
            pass

    async def get_checkpoint(self, job_id: str) -> Dict[str, Any]:
        from app.infrastructure.checkpoints import checkpointer_status
        from app.workflows.graph import graph_backend

        config = thread_config(job_id)
        try:
            snap = await self.app_graph.aget_state(config)
        except Exception as exc:
            return {
                "thread_id": job_id,
                "exists": False,
                "error": str(exc),
                "checkpointer": checkpointer_status(),
                "graph_backend": graph_backend(),
            }

        values = getattr(snap, "values", None) or {}
        next_nodes = list(getattr(snap, "next", None) or [])
        return {
            "thread_id": job_id,
            "exists": bool(values) or bool(next_nodes),
            "next": next_nodes,
            "values": values,
            "config": getattr(snap, "config", None),
            "checkpointer": checkpointer_status(),
            "graph_backend": graph_backend(),
        }

    async def stream_workflow(
        self,
        job_id: str,
        user_id: str,
        *,
        resume: bool = False,
    ) -> AsyncGenerator[str, None]:
        # Real Tracker jobs must belong to the caller (demo UUID is allowed for mock runs)
        demo_id = "00000000-0000-0000-0000-000000000000"
        if job_id != demo_id:
            try:
                from app.infrastructure.db.models import DBJob

                jid = UUID(job_id)
                uid = UUID(user_id)
                async with async_session() as session:
                    result = await session.execute(
                        select(DBJob).where(DBJob.id == jid, DBJob.user_id == uid)
                    )
                    if not result.scalars().first():
                        yield (
                            "data: "
                            + json.dumps(
                                {
                                    "type": "ERROR",
                                    "node": "System",
                                    "application_id": job_id,
                                    "error": "Job not found for this account. Pick a Tracker job you own.",
                                }
                            )
                            + "\n\n"
                        )
                        return
            except (ValueError, TypeError):
                yield (
                    "data: "
                    + json.dumps(
                        {
                            "type": "ERROR",
                            "node": "System",
                            "application_id": job_id,
                            "error": "Invalid job_id",
                        }
                    )
                    + "\n\n"
                )
                return

        initial_state = {
            "job_id": job_id,
            "user_id": user_id,
            "resume_id": None,
            "messages": [],
            "job_details": {},
            "job_url": None,
            "company_research": {},
            "ats_score": None,
            "missing_skills": [],
            "tailored_resume": {},
            "requires_human_approval": False,
        }
        config = thread_config(job_id)
        queue = event_bus.register(CHANNEL)

        async def run_graph():
            graph = self.app_graph
            try:
                await asyncio.sleep(0.05)
                final_state = dict(initial_state)

                if resume:
                    # Continue from last checkpoint (None input = resume)
                    stream = graph.astream(None, config)
                    await event_bus.publish(
                        CHANNEL,
                        {
                            "type": "SYSTEM",
                            "node": "System",
                            "application_id": job_id,
                            "message": "Resuming workflow from LangGraph checkpoint…",
                        },
                    )
                else:
                    stream = graph.astream(initial_state, config)

                async for chunk in stream:
                    for _node_name, state_updates in chunk.items():
                        if isinstance(state_updates, dict):
                            final_state.update(state_updates)

                # Refresh from checkpointer for authoritative values
                try:
                    snap = await graph.aget_state(config)
                    if getattr(snap, "values", None):
                        final_state.update(snap.values)
                except Exception:
                    pass

                await self._persist_checkpoint_meta(
                    job_id, user_id, final_state, status="completed"
                )

                await event_bus.publish(
                    CHANNEL,
                    {
                        "type": "COMPLETED",
                        "application_id": job_id,
                        "node": "System",
                        "final_state": {
                            **final_state,
                            "job_id": job_id,
                            "user_id": user_id,
                        },
                    },
                )
            except Exception as e:
                await event_bus.publish(
                    CHANNEL,
                    {
                        "type": "ERROR",
                        "error": str(e),
                        "application_id": job_id,
                        "node": "System",
                    },
                )

        task = asyncio.create_task(run_graph())
        mode = "resume" if resume else "start"
        yield (
            f"data: {json.dumps({'type': 'SYSTEM', 'node': 'System', 'application_id': job_id, 'message': f'Workflow engine connected ({mode}). Agents starting…'})}\n\n"
        )

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=300.0)
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'ERROR', 'node': 'System', 'application_id': job_id, 'error': 'Workflow timed out waiting for events'})}\n\n"
                    break

                if event.get("application_id") not in (None, job_id):
                    continue

                yield f"data: {json.dumps(event)}\n\n"

                if event.get("type") in ("COMPLETED", "ERROR"):
                    break
        except asyncio.CancelledError:
            task.cancel()
            raise
        finally:
            event_bus.unregister(CHANNEL, queue)
            if not task.done():
                task.cancel()
