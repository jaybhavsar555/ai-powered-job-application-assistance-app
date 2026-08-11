from pydantic import BaseModel, Field
from typing import List, Dict, Any

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.core.prompts.registry import prompt_registry
from app.infrastructure.llm.client import structured_generate

class OptimizedResume(BaseModel):
    summary: str = Field(..., description="A newly tailored professional summary targeting the specific role")
    tailored_bullets: List[str] = Field(..., description="Top 5 most relevant experience bullets, re-written to include missing keywords where factually accurate")
    added_keywords: List[str] = Field(..., description="Keywords successfully woven into the resume")

class ResumeOptimizerAgent(OSAgent):
    name = "resume_optimizer"
    description = "Rewrites resume bullet points to naturally incorporate missing ATS keywords."
    capabilities = ["write"]

    def _mock(self, missing_skills: List[str]) -> OptimizedResume:
        skills = [s for s in (missing_skills or []) if s][:6]
        skill_line = ", ".join(skills) if skills else "core stack listed in the JD"
        return OptimizedResume(
            summary=(
                f"Engineer with hands-on delivery experience; emphasizing "
                f"{skill_line} to match this role. "
                "(AI was unavailable — keyword-focused draft; re-run Tailor when LLM is free.)"
            ),
            tailored_bullets=[
                f"Delivered production features using {skills[0]}." if skills else "Delivered production features aligned to the role requirements.",
                f"Collaborated across teams while applying {skills[1]}." if len(skills) > 1 else "Collaborated with product and design to ship user-facing work.",
                "Owned debugging, testing, and iterative improvement of shipped features.",
            ],
            added_keywords=skills[:5],
        )

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        base_resume = state.get("resume_json", "{}")
        missing_skills = state.get("ats_score", {}).get("missing_skills", [])
        job_details = state.get("job_description", "")
        memories = state.get("long_term_memory", [])
        
        memory_str = ""
        if memories:
            memory_str = "Relevant Memories from Vault:\n" + "\n".join(
                f"- [{m['type']}] {m['title']}: {m['content']}" for m in memories
            )

        system_prompt = prompt_registry.get_prompt(self.name)

        result = await structured_generate(
            OptimizedResume,
            [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Base Resume:\n{(base_resume or '')[:1200]}\n\n"
                        f"Missing ATS Skills:\n{', '.join(missing_skills)}\n\n"
                        f"{memory_str}\n\n"
                        f"Job Details:\n{(job_details or '')[:1800]}"
                    ),
                },
            ],
            fallback=lambda: self._mock(missing_skills),
        )
        return {"optimized_resume": result.model_dump()}

agent_registry.register(ResumeOptimizerAgent())
