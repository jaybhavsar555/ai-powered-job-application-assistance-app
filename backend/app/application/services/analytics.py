from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from uuid import UUID
from collections import defaultdict
from app.infrastructure.db.models import DBAgentEventLog, DBApplication
from app.schemas.analytics import (
    AnalyticsSummary,
    AgentBreakdown,
    StageCount,
    RecentEvent,
    INPUT_TOKEN_COST,
    OUTPUT_TOKEN_COST,
)

def _estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * INPUT_TOKEN_COST) + (output_tokens * OUTPUT_TOKEN_COST)

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(self, user_id: UUID) -> AnalyticsSummary:
        # Event logs scoped to the user's applications
        events_result = await self.db.execute(
            select(DBAgentEventLog)
            .join(DBApplication, DBAgentEventLog.application_id == DBApplication.id)
            .where(DBApplication.user_id == user_id)
            .order_by(DBAgentEventLog.created_at.desc())
        )
        events = list(events_result.scalars().all())

        apps_result = await self.db.execute(
            select(DBApplication.stage, func.count(DBApplication.id))
            .where(DBApplication.user_id == user_id)
            .group_by(DBApplication.stage)
        )
        pipeline_rows = apps_result.all()
        applications_tracked = sum(row[1] for row in pipeline_rows)
        pipeline = [
            StageCount(stage=row[0] or "Unknown", count=row[1])
            for row in pipeline_rows
        ]

        total_input = 0
        total_output = 0
        total_latency = 0
        successes = 0
        errors = 0

        by_agent: dict = defaultdict(lambda: {
            "runs": 0,
            "successes": 0,
            "errors": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_latency_ms": 0,
        })

        for ev in events:
            is_error = ev.action_type == "error"
            total_input += ev.input_tokens or 0
            total_output += ev.output_tokens or 0
            total_latency += ev.latency_ms or 0
            if is_error:
                errors += 1
            else:
                successes += 1

            bucket = by_agent[ev.agent_name]
            bucket["runs"] += 1
            bucket["input_tokens"] += ev.input_tokens or 0
            bucket["output_tokens"] += ev.output_tokens or 0
            bucket["total_latency_ms"] += ev.latency_ms or 0
            if is_error:
                bucket["errors"] += 1
            else:
                bucket["successes"] += 1

        total_runs = successes + errors
        success_rate = (successes / total_runs * 100.0) if total_runs else 0.0
        avg_latency = (total_latency / total_runs) if total_runs else 0.0

        agents = []
        for name, b in sorted(by_agent.items(), key=lambda x: x[1]["runs"], reverse=True):
            agent_runs = b["runs"]
            agents.append(AgentBreakdown(
                agent_name=name,
                runs=agent_runs,
                successes=b["successes"],
                errors=b["errors"],
                success_rate=(b["successes"] / agent_runs * 100.0) if agent_runs else 0.0,
                input_tokens=b["input_tokens"],
                output_tokens=b["output_tokens"],
                total_tokens=b["input_tokens"] + b["output_tokens"],
                total_latency_ms=b["total_latency_ms"],
                avg_latency_ms=(b["total_latency_ms"] / agent_runs) if agent_runs else 0.0,
                estimated_cost=_estimate_cost(b["input_tokens"], b["output_tokens"]),
            ))

        recent_events = [
            RecentEvent(
                id=ev.id,
                agent_name=ev.agent_name,
                action_type=ev.action_type,
                input_tokens=ev.input_tokens or 0,
                output_tokens=ev.output_tokens or 0,
                latency_ms=ev.latency_ms or 0,
                estimated_cost=_estimate_cost(ev.input_tokens or 0, ev.output_tokens or 0),
                application_id=ev.application_id,
                created_at=ev.created_at,
            )
            for ev in events[:25]
        ]

        return AnalyticsSummary(
            total_runs=total_runs,
            successes=successes,
            errors=errors,
            success_rate=round(success_rate, 1),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_input + total_output,
            total_latency_ms=total_latency,
            avg_latency_ms=round(avg_latency, 1),
            estimated_cost=round(_estimate_cost(total_input, total_output), 6),
            applications_tracked=applications_tracked,
            agents=agents,
            pipeline=pipeline,
            recent_events=recent_events,
        )
