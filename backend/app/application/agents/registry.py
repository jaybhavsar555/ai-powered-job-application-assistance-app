from typing import Dict, Type
from .base import OSAgent

class AgentRegistry:
    """
    Central registry for all active agents in the system.
    This replaces hardcoded imports in the workflow graph.
    """
    _agents: Dict[str, OSAgent] = {}

    @classmethod
    def register(cls, agent: OSAgent):
        cls._agents[agent.name] = agent
        print(f"[Registry] Registered agent: {agent.name}")

    @classmethod
    def get_agent(cls, name: str) -> OSAgent:
        if name not in cls._agents:
            raise ValueError(f"Agent '{name}' not found in registry.")
        return cls._agents[name]

    @classmethod
    def list_agents(cls) -> Dict[str, dict]:
        return {
            name: {
                "description": agent.description,
                "capabilities": agent.capabilities
            }
            for name, agent in cls._agents.items()
        }

# Global registry instance
agent_registry = AgentRegistry()
