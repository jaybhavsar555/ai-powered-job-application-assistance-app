from pydantic import BaseModel, Field
from typing import List, Optional


class AgentInfo(BaseModel):
    name: str
    label: str
    description: str
    capabilities: List[str] = Field(default_factory=list)
    system_prompt: Optional[str] = None
    configurable: bool = True
    role: str = "agent"  # agent | human


class AgentPromptUpdate(BaseModel):
    system_prompt: str = Field(..., min_length=1)
    persist: bool = True


class AgentPromptResponse(BaseModel):
    name: str
    system_prompt: str
    persisted: bool
