from typing import Dict, Any, List
from pydantic import BaseModel, Field

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.core.prompts.registry import prompt_registry
from app.infrastructure.llm.client import structured_generate
# In a real scenario, this would use a SERP API or Hunter.io API.
# For now, we will mock the gathering or use the LLM to infer based on domain.

class RecruiterDiscoveryResult(BaseModel):
    recruiter_name: str = Field(..., description="Name of the recruiter or 'Hiring Team'")
    recruiter_email: str = Field(..., description="Email address found or inferred")
    confidence: float = Field(..., description="Confidence score between 0 and 1")
    sources: List[str] = Field(default_factory=list)

class RecruiterDiscoveryAgent(OSAgent):
    name = "recruiter_discovery_agent"
    description = "Finds or infers HR/Recruiter emails for cold outreach."
    capabilities = ["web", "llm"]

    def _mock(self, company: str) -> RecruiterDiscoveryResult:
        domain = company.lower().replace(" ", "") + ".com"
        return RecruiterDiscoveryResult(
            recruiter_name="Hiring Team",
            recruiter_email=f"careers@{domain}",
            confidence=0.5,
            sources=["mock://domain-inference"]
        )

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        job = state.get("job_details") or {}
        company = state.get("company_research", {}).get("company_name") or job.get("company_name", "Unknown Company")
        job_url = state.get("job_url", "")
        
        system_prompt = prompt_registry.get_prompt(self.name)

        # In a real implementation, you would call your SERP scraping function here.
        # e.g., raw_search_results = await search_google(f"{company} recruiter email")
        raw_search_results = f"Search results for {company} HR recruiter email: \n- No public email found on LinkedIn. \n- Website domain is likely {company.lower().replace(' ', '')}.com"

        result = await structured_generate(
            RecruiterDiscoveryResult,
            [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Company: {company}\n"
                        f"Job Title: {job.get('role_title', '')}\n"
                        f"Job URL: {job_url}\n\n"
                        f"Web Search Results:\n{raw_search_results}"
                    )
                }
            ],
            fallback=lambda: self._mock(company),
        )
        
        return {"recruiter_discovery": result.model_dump()}

agent_registry.register(RecruiterDiscoveryAgent())
