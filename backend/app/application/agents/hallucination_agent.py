import json
import logging
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from textwrap import dedent

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.infrastructure.llm.client import structured_generate

logger = logging.getLogger(__name__)


class HallucinationReport(BaseModel):
    has_hallucination: bool = Field(
        description="True if tailored resume contains claims not in base resume / Q&A."
    )
    hallucinated_claims: List[str] = Field(
        description="List of hallucinated claims. Empty if none."
    )
    explanation: str = Field(description="Why claims were flagged, or why it passed.")


class HallucinationAgent(OSAgent):
    """Strict auditor: base resume vs tailored output for fabricated claims."""

    name = "hallucination_checker"
    description = "Flags fabricated skills/metrics in tailored resumes."
    capabilities = ["read"]

    def __init__(self) -> None:
        self.system_prompt = dedent(
            """
            You are a strict resume auditor. Flag any claim, skill, metric, employer,
            or date in the tailored resume that is not supported by the base resume
            or approved Q&A. Prefer false negatives over letting fabrications through.
            """
        ).strip()

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        base = state.get("resume_json") or state.get("base_resume") or ""
        tailored = state.get("optimized_resume") or state.get("tailored_resume") or {}
        if hasattr(tailored, "model_dump"):
            tailored = tailored.model_dump()
        qa = state.get("screening_qa") or state.get("long_term_memory") or []

        def fallback() -> HallucinationReport:
            return HallucinationReport(
                has_hallucination=False,
                hallucinated_claims=[],
                explanation="Mock auditor — no LLM; assumed clean.",
            )

        report = await structured_generate(
            HallucinationReport,
            [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"BASE RESUME:\n{base}\n\n"
                        f"TAILORED:\n{json.dumps(tailored, indent=2)}\n\n"
                        f"APPROVED Q&A / MEMORY:\n{json.dumps(qa, indent=2)}"
                    ),
                },
            ],
            fallback=fallback,
            max_tokens=500,
        )
        return {"hallucination_report": report.model_dump()}


agent_registry.register(HallucinationAgent())
