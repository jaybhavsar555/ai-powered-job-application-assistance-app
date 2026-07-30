from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.core.prompts.registry import prompt_registry
from app.infrastructure.llm.client import structured_generate
from app.infrastructure.scraping.company_research import gather_company_signals


class CompanyResearchResult(BaseModel):
    company_name: str = Field(..., description="Canonical company name")
    summary: str = Field(..., description="2-4 sentence company overview")
    industry: Optional[str] = Field(None, description="Primary industry")
    tech_stack: List[str] = Field(default_factory=list, description="Likely tech / product stack")
    recent_news_hooks: List[str] = Field(
        default_factory=list,
        description="Concrete hooks for a cover letter (funding, products, news)",
    )
    culture_signals: List[str] = Field(default_factory=list)
    funding_or_stage: Optional[str] = Field(None, description="e.g. Series B, public, startup")
    sources: List[str] = Field(default_factory=list)


class CompanyResearchAgent(OSAgent):
    name = "company_research_agent"
    description = "Researches the target company for cover-letter hooks and context."
    capabilities = ["web"]

    def _mock(self, company: str) -> CompanyResearchResult:
        name = company or "Tech Corp"
        return CompanyResearchResult(
            company_name=name,
            summary=(
                f"{name} builds cloud-native developer tooling with a focus on "
                "reliable backend systems and AI-assisted workflows."
            ),
            industry="Enterprise Software",
            tech_stack=["Python", "Kubernetes", "AWS"],
            recent_news_hooks=[
                "Recent Series B funding to scale platform engineering",
                "Push into Kubernetes-based deployment automation",
            ],
            culture_signals=["Remote-friendly", "Strong engineering ownership"],
            funding_or_stage="Series B",
            sources=["mock://company-research"],
        )

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        job = state.get("job_details") or {}
        company = (
            state.get("company")
            or job.get("company_name")
            or "Unknown Company"
        )
        job_url = state.get("job_url")
        system_prompt = prompt_registry.get_prompt(self.name)

        signals = await gather_company_signals(company, job_url)

        result = await structured_generate(
            CompanyResearchResult,
            [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Company: {company}\n"
                        f"Job title: {job.get('role_title', state.get('title', ''))}\n"
                        f"Research source: {signals.source}\n"
                        f"Sources: {', '.join(signals.sources)}\n\n"
                        f"Raw research text:\n{(signals.raw_text or '')[:2000]}"
                    ),
                },
            ],
            fallback=lambda: self._mock(company),
        )
        payload = result.model_dump()
        if not payload.get("sources"):
            payload["sources"] = signals.sources
        payload["_gather"] = {
            "source": signals.source,
            "error": signals.error,
        }
        return {"company_research": payload}


agent_registry.register(CompanyResearchAgent())
