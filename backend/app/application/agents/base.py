from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
import time
import uuid

from app.infrastructure.events.bus import event_bus
from app.infrastructure.db.session import async_session
from app.infrastructure.db.models import DBAgentEventLog

class OSAgent(ABC):
    """
    Base class for all Agents in the Career Operating System.
    Handles standardizing inputs, wrapping execution for telemetry, and emitting events.
    """
    name: str = "BaseAgent"
    description: str = "Base agent description"
    capabilities: List[str] = [] # e.g., 'web', 'db', 'terminal'

    @abstractmethod
    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        """
        The core execution logic of the agent. Must return a dict to update LangGraph state.
        """
        pass

    async def execute(self, state: Dict[str, Any], application_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Wrapper around `run` that calculates telemetry (latency, tokens) and handles errors.
        In Phase 5, this will emit to Redis Event Bus.
        """
        start_time = time.time()
        
        # Publish START event
        await event_bus.publish("workflow_events", {
            "type": "AGENT_STARTED",
            "node": self.name,
            "application_id": application_id
        })
        
        try:
            result = await self.run(state)
            
            latency = int((time.time() - start_time) * 1000)
            mock_input_tokens = 120
            mock_output_tokens = 45
            
            # Save to Postgres
            if application_id:
                async with async_session() as session:
                    log_entry = DBAgentEventLog(
                        application_id=uuid.UUID(application_id),
                        agent_name=self.name,
                        action_type="execution",
                        input_tokens=mock_input_tokens,
                        output_tokens=mock_output_tokens,
                        latency_ms=latency,
                        evidence=result
                    )
                    session.add(log_entry)
                    await session.commit()
            
            # Publish SUCCESS event
            await event_bus.publish("workflow_events", {
                "type": "AGENT_SUCCESS",
                "node": self.name,
                "application_id": application_id,
                "latency_ms": latency,
                "tokens": mock_input_tokens + mock_output_tokens,
                "cost": (mock_input_tokens * 0.000005) + (mock_output_tokens * 0.000015),
                "evidence": result
            })
            
            print(f"[{self.name}] Completed in {latency}ms | In: {mock_input_tokens} | Out: {mock_output_tokens}")
            
            return result
            
        except Exception as e:
            # Publish ERROR event
            await event_bus.publish("workflow_events", {
                "type": "AGENT_ERROR",
                "node": self.name,
                "application_id": application_id,
                "error": str(e)
            })
            print(f"[{self.name}] Error: {str(e)}")
            raise e
