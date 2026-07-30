from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime

# Matches OSAgent.execute pricing heuristic
INPUT_TOKEN_COST = 0.000005
OUTPUT_TOKEN_COST = 0.000015

class AgentBreakdown(BaseModel):
    agent_name: str
    runs: int
    successes: int
    errors: int
    success_rate: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    total_latency_ms: int
    avg_latency_ms: float
    estimated_cost: float

class StageCount(BaseModel):
    stage: str
    count: int

class RecentEvent(BaseModel):
    id: UUID
    agent_name: str
    action_type: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    estimated_cost: float
    application_id: Optional[UUID] = None
    created_at: datetime

class AnalyticsSummary(BaseModel):
    total_runs: int
    successes: int
    errors: int
    success_rate: float
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_latency_ms: int
    avg_latency_ms: float
    estimated_cost: float
    applications_tracked: int
    agents: List[AgentBreakdown]
    pipeline: List[StageCount]
    recent_events: List[RecentEvent]
