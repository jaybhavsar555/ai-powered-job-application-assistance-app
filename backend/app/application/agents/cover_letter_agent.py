from pydantic import BaseModel, Field
from typing import Any, Dict
import json

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.core.prompts.registry import prompt_registry
from app.infrastructure.llm.client import structured_generate


def _as_prompt_text(value: Any, limit: int = 1500) -> str:
    """Coerce dict/list/str payloads into a truncated prompt string."""
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, default=str)
    else:
        text = str(value)
    return text[:limit]


class CoverLetter(BaseModel):
    content: str = Field(..., description="The full, professional cover letter text, properly formatted with paragraphs")
    hooks_used: list[str] = Field(..., description="The specific pain points or company research used as hooks in the introduction")


class CoverLetterAgent(OSAgent):
    name = "cover_letter_agent"
    description = "Generates highly personalized cover letters using the candidate's resume, job details, and company research."
    capabilities = ["write"]

    def _mock(self) -> CoverLetter:
        return CoverLetter(
            content="Dear Hiring Manager,\n\nI am thrilled to apply for this position. Given your recent Series B funding and focus on scaling Kubernetes, my background in deploying highly available microservices makes me an ideal fit.\n\nSincerely,\nThe Candidate",
            hooks_used=["Series B funding", "Kubernetes scaling"],
        )

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        optimized_resume = state.get("optimized_resume", "{}")
        job_details = state.get("job_description", "")
        company_research = state.get("company_research", "No research found.")
        memories = state.get("long_term_memory", [])
        
        memory_str = ""
        if memories:
            memory_str = "Relevant Memories from Vault:\n" + "\n".join(
                f"- [{m.get('type', 'info')}] {m.get('title', '')}: {m.get('content', '')}" for m in memories
            )

        system_prompt = prompt_registry.get_prompt(self.name)

        result = await structured_generate(
            CoverLetter,
            [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Write a concise cover letter (max ~180 words, 3 short paragraphs).\n\n"
                        f"Resume:\n{_as_prompt_text(optimized_resume)}\n\n"
                        f"Job Details:\n{_as_prompt_text(job_details)}\n\n"
                        f"Company Research:\n{_as_prompt_text(company_research)}\n\n"
                        f"{memory_str}"
                    ),
                },
            ],
            fallback=self._mock,
        )
        return {"cover_letter": result.model_dump()}


agent_registry.register(CoverLetterAgent())
