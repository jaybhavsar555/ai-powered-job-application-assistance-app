from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.core.config import get_settings
from app.core.prompts.registry import prompt_registry


class RecruiterDiscoveryResult(BaseModel):
    recruiter_name: str = Field(..., description="Name of the recruiter or 'Hiring Team'")
    recruiter_email: str = Field(..., description="Email address found or inferred")
    confidence: float = Field(..., description="Confidence score between 0 and 1")
    sources: List[str] = Field(default_factory=list)
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL if known")


def _domain_from_job_url(job_url: str) -> Optional[str]:
    if not job_url:
        return None
    host = (urlparse(job_url).hostname or "").lower().removeprefix("www.")
    if not host:
        return None
    # Skip ATS hosts — they are not the company domain
    ats = (
        "greenhouse.io",
        "lever.co",
        "ashbyhq.com",
        "myworkdayjobs.com",
        "linkedin.com",
        "indeed.com",
        "boards.eu",
    )
    if any(a in host for a in ats):
        return None
    return host


def _guess_domain(company: str, job_url: str) -> Optional[str]:
    from_url = _domain_from_job_url(job_url)
    if from_url:
        return from_url
    slug = "".join(c for c in (company or "").lower() if c.isalnum())
    if len(slug) >= 3:
        return f"{slug}.com"
    return None


async def _hunter_domain_search(domain: str, api_key: str) -> Optional[RecruiterDiscoveryResult]:
    """Hunter.io domain-search — returns best person email or None."""
    url = "https://api.hunter.io/v2/domain-search"
    params = {
        "domain": domain,
        "api_key": api_key,
        "limit": 5,
        "seniority": "junior,senior,executive",
        "department": "hr,recruiting",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url, params=params)
        if resp.status_code == 401:
            print("[recruiter_discovery] Hunter API key rejected (401)")
            return None
        if resp.status_code == 429:
            print("[recruiter_discovery] Hunter rate limited (429)")
            return None
        resp.raise_for_status()
        data = resp.json().get("data") or {}

    emails = data.get("emails") or []
    # Prefer recruiting/hr titles, then any with confidence
    def score(row: dict) -> tuple:
        pos = (row.get("position") or "").lower()
        hrish = 1 if any(k in pos for k in ("recruit", "talent", "people", "hr")) else 0
        return (hrish, int(row.get("confidence") or 0))

    emails = sorted(emails, key=score, reverse=True)
    for row in emails:
        value = (row.get("value") or "").strip()
        if not value or "@" not in value:
            continue
        first = (row.get("first_name") or "").strip()
        last = (row.get("last_name") or "").strip()
        name = f"{first} {last}".strip() or "Hiring Team"
        conf = float(row.get("confidence") or 0) / 100.0
        linkedin = (row.get("linkedin") or "").strip() or None
        return RecruiterDiscoveryResult(
            recruiter_name=name,
            recruiter_email=value,
            confidence=max(0.0, min(conf, 1.0)),
            sources=[f"hunter://{domain}"],
            linkedin_url=linkedin,
        )

    # Pattern-only domain (no person) — still useful as careers@ hint? Skip inventing.
    return None


class RecruiterDiscoveryAgent(OSAgent):
    name = "recruiter_discovery_agent"
    description = "Finds or infers HR/Recruiter emails for cold outreach."
    capabilities = ["web", "llm"]

    def _unavailable(self, company: str, reason: str) -> RecruiterDiscoveryResult:
        return RecruiterDiscoveryResult(
            recruiter_name="Hiring Team",
            recruiter_email="",
            confidence=0.0,
            sources=["unavailable"],
            linkedin_url=None,
        )

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        job = state.get("job_details") or {}
        company = (
            state.get("company_research", {}).get("company_name")
            or job.get("company_name", "Unknown Company")
        )
        job_url = state.get("job_url", "") or ""

        _ = prompt_registry.get_prompt(self.name)
        settings = get_settings()
        api_key = (settings.HUNTER_API_KEY or "").strip()

        if api_key:
            domain = _guess_domain(company, job_url)
            if domain:
                try:
                    found = await _hunter_domain_search(domain, api_key)
                    if found and found.recruiter_email:
                        payload = found.model_dump()
                        payload["_unavailable"] = False
                        payload["_reason"] = f"Hunter domain-search for {domain}"
                        return {"recruiter_discovery": payload}
                    print(
                        f"[recruiter_discovery] Hunter found no person email for {domain}"
                    )
                except Exception as exc:
                    print(f"[recruiter_discovery] Hunter failed: {exc}")

        result = self._unavailable(
            company,
            "No Hunter key or no match — paste email/LinkedIn in Outreach",
        )
        payload = result.model_dump()
        payload["_unavailable"] = True
        payload["_reason"] = (
            "Live recruiter lookup unavailable. "
            "Paste email or LinkedIn on Outreach before send. "
            f"Company={company} job_url={job_url or 'n/a'} "
            f"hunter_configured={bool(api_key)}"
        )
        return {"recruiter_discovery": payload}


agent_registry.register(RecruiterDiscoveryAgent())
