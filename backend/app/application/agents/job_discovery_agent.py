"""Multi-source job discovery: Remotive + RemoteOK + Arbeitnow, then LLM score."""

from __future__ import annotations

import logging
import re
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from app.infrastructure.llm.client import structured_generate
from app.infrastructure.resume_library import list_resume_files, extract_text
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DiscoveredJob(BaseModel):
    id: str = Field(description="A unique ID for the job")
    company: str
    title: str
    location: str
    salary: str
    description: str
    matchScore: int = Field(description="A score out of 100 on how well the user matches")
    matchReason: str = Field(
        description="Why the user is a strong fit based on their resume"
    )
    company_info: Optional[str] = Field(default=None, description="A brief blurb about the hiring firm extracted from the JD")
    contact_info: Optional[str] = Field(default=None, description="Any recruiter name or email found in the JD")
    full_jd: Optional[str] = Field(default=None, description="The full raw job description (populated server-side)")
    url: Optional[str] = Field(default=None, description="Canonical job posting URL")
    source: Optional[str] = Field(default=None, description="remotive|remoteok|arbeitnow")
    posted_at: Optional[str] = Field(default=None, description="ISO date if known")


class JobDiscoveryResponse(BaseModel):
    jobs: List[DiscoveredJob]


def clean_html(raw_html: str) -> str:
    try:
        from bs4 import BeautifulSoup

        return BeautifulSoup(raw_html, "html.parser").get_text(separator=" ", strip=True)
    except Exception:
        return re.sub(r"<.*?>", "", raw_html or "")


def _iso_from_epoch(ts: Any) -> Optional[str]:
    try:
        if ts is None:
            return None
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
        s = str(ts).strip()
        if s.isdigit():
            return datetime.fromtimestamp(float(s), tz=timezone.utc).isoformat()
        return s
    except Exception:
        return None


class JobDiscoveryAgent:
    def __init__(self, llm_service=None, knowledge_service=None):
        self.llm = llm_service
        self.knowledge = knowledge_service

    async def fetch_remotive(self, search_term: str, limit: int) -> List[Dict[str, Any]]:
        """
        For each job:
        1. Evaluate if it matches the User Preferences (especially Remote vs Hybrid vs Location, and strictly ensuring it is a relevant Tech Role).
        2. Give it a matchScore from 0-100 based on how well the Resume aligns.
        3. If it is NOT a Tech Role or completely violates the remote/hybrid preference, discard it.
        4. CRITICAL: If the job appears EXPIRED, CLOSED, or is older than 30 days, discard it immediately.
        5. Provide an analysis (pros and cons).

        Return ONLY JSON in this format:
        {
          "recommendedJobs": [
            {
              "id": "exact id from the job posting",
              "title": "exact title from the job posting",
              "company": "exact company name",
              "location": "location string",
              "matchScore": 85,
              "analysis": "Pros: ..., Cons: ...",
              "firm_overview": "A brief AI-generated summary of what this firm does (if known)",
              "contact_info": "Any recruiter contact info or apply URL found"
            }
          ]
        }
        """
        url = f"https://remotive.com/api/remote-jobs?search={search_term}"
        try:
            async with httpx.AsyncClient(headers={"User-Agent": "CareerOS/1.0"}) as client:
                response = await client.get(url, timeout=12.0)
                if response.status_code != 200:
                    return []
                jobs = response.json().get("jobs") or []
                out = []
                for j in jobs[:limit]:
                    out.append(
                        {
                            "id": f"remotive-{j.get('id')}",
                            "title": j.get("title") or "",
                            "company_name": j.get("company_name") or "",
                            "candidate_required_location": j.get(
                                "candidate_required_location", "Remote"
                            ),
                            "salary": j.get("salary") or "Competitive",
                            "url": j.get("url"),
                            "description": j.get("description") or "",
                            "publication_date": j.get("publication_date"),
                            "source": "remotive",
                        }
                    )
                return out
        except Exception as e:
            logger.error("Remotive fetch failed: %s", e)
            return []

    async def fetch_remoteok(self, search_term: str, limit: int) -> List[Dict[str, Any]]:
        # Public JSON feed; filter client-side by search term
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": "CareerOS/1.0"}
            ) as client:
                response = await client.get("https://remoteok.com/api", timeout=12.0)
                if response.status_code != 200:
                    return []
                data = response.json()
                if not isinstance(data, list):
                    return []
                term = (search_term or "").lower()
                out = []
                for j in data:
                    if not isinstance(j, dict) or not j.get("id") or j.get("id") == "legal":
                        continue
                    blob = f"{j.get('position','')} {j.get('company','')} {' '.join(j.get('tags') or [])}".lower()
                    if term and term not in blob:
                        continue
                    out.append(
                        {
                            "id": f"remoteok-{j.get('id')}",
                            "title": j.get("position") or j.get("title") or "",
                            "company_name": j.get("company") or "",
                            "candidate_required_location": j.get("location") or "Remote",
                            "salary": (
                                f"{j.get('salary_min')}-{j.get('salary_max')}"
                                if j.get("salary_min")
                                else "Competitive"
                            ),
                            "url": j.get("url") or j.get("apply_url"),
                            "description": j.get("description") or "",
                            "publication_date": _iso_from_epoch(j.get("epoch") or j.get("date")),
                            "source": "remoteok",
                        }
                    )
                    if len(out) >= limit:
                        break
                return out
        except Exception as e:
            logger.error("RemoteOK fetch failed: %s", e)
            return []

    async def fetch_arbeitnow(self, search_term: str, limit: int) -> List[Dict[str, Any]]:
        try:
            params = {"page": 1}
            if search_term:
                # Arbeitnow uses full search via query when available
                pass
            async with httpx.AsyncClient(
                headers={"User-Agent": "CareerOS/1.0"}
            ) as client:
                response = await client.get(
                    "https://www.arbeitnow.com/api/job-board-api",
                    params=params,
                    timeout=12.0,
                )
                if response.status_code != 200:
                    return []
                data = response.json().get("data") or []
                term = (search_term or "").lower()
                out = []
                for j in data:
                    title = j.get("title") or ""
                    company = j.get("company_name") or ""
                    blob = f"{title} {company} {' '.join(j.get('tags') or [])}".lower()
                    if term and term not in blob and term.split()[0] not in blob:
                        continue
                    out.append(
                        {
                            "id": f"arbeitnow-{j.get('slug') or j.get('url')}",
                            "title": title,
                            "company_name": company,
                            "candidate_required_location": j.get("location") or "Remote",
                            "salary": "Competitive",
                            "url": j.get("url"),
                            "description": j.get("description") or "",
                            "publication_date": _iso_from_epoch(j.get("created_at")),
                            "source": "arbeitnow",
                        }
                    )
                    if len(out) >= limit:
                        break
                # If filter emptied list, take first N unfiltered
                if not out:
                    for j in data[:limit]:
                        out.append(
                            {
                                "id": f"arbeitnow-{j.get('slug') or j.get('url')}",
                                "title": j.get("title") or "",
                                "company_name": j.get("company_name") or "",
                                "candidate_required_location": j.get("location") or "Remote",
                                "salary": "Competitive",
                                "url": j.get("url"),
                                "description": j.get("description") or "",
                                "publication_date": _iso_from_epoch(j.get("created_at")),
                                "source": "arbeitnow",
                            }
                        )
                return out
        except Exception as e:
            logger.error("Arbeitnow fetch failed: %s", e)
            return []

    async def fetch_vault_portals(self, search_term: str, location: str, limit: int) -> List[Dict[str, Any]]:
        from app.core.job_portals import JOB_PORTALS
        import urllib.parse
        from bs4 import BeautifulSoup
        
        # Build query: site:instahyre.com OR site:wellfound.com "Software Engineer" "hybrid"
        site_str = " OR ".join([f"site:{urllib.parse.urlparse(p['url']).netloc}" for p in JOB_PORTALS[:10]])
        query = f'({site_str} OR "careers") "{search_term}" "{location}"'
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}&df=m"
        
        try:
            async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as client:
                response = await client.get(url, timeout=12.0)
                if response.status_code != 200:
                    return []
                soup = BeautifulSoup(response.text, "html.parser")
                results = soup.find_all("a", class_="result__url")
                snippets = soup.find_all("a", class_="result__snippet")
                
                out = []
                for i in range(min(limit, len(results))):
                    link = results[i].get("href")
                    if link and "uddg=" in link:
                        link = urllib.parse.unquote(link.split("uddg=")[1].split("&")[0])
                    elif link and link.startswith("/"):
                        link = f"https://duckduckgo.com{link}"
                        
                    snippet = snippets[i].get_text(strip=True) if i < len(snippets) else ""
                    
                    if link:
                        out.append({
                            "id": f"vault-{hash(link)}",
                            "title": f"Vault Match: {search_term.title()}", 
                            "company_name": "Vault Job Portal",
                            "candidate_required_location": location or "Hybrid/Remote",
                            "salary": "Competitive",
                            "url": link,
                            "description": snippet,
                            "publication_date": None,
                            "source": "vault_portals",
                        })
                return out
        except Exception as e:
            logger.error("Vault portal fetch failed: %s", e)
            return []

    async def fetch_live_jobs(self, target_roles: str, is_remote: bool, location_hubs: list[str]) -> List[Dict[str, Any]]:
        settings = get_settings()
        search_term = (
            target_roles.split(",")[0].strip() if target_roles else "software engineer"
        )
        location = "Remote" if is_remote else (location_hubs[0] if location_hubs else "Hybrid")
        per = max(2, int(settings.JOB_DISCOVERY_PER_SOURCE or 4))
        sources = settings.job_discovery_source_list() or ["remotive", "vault_portals"]
        combined: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()

        fetchers = {
            "remotive": self.fetch_remotive,
            "remoteok": self.fetch_remoteok,
            "arbeitnow": self.fetch_arbeitnow,
            "vault_portals": lambda term, limit: self.fetch_vault_portals(term, location, limit),
        }
        for src in sources:
            fn = fetchers.get(src)
            if not fn:
                continue
            try:
                batch = await fn(search_term, per)
            except Exception as e:
                logger.error("Source %s failed: %s", src, e)
                batch = []
            for j in batch:
                from app.application.services.job_urls import normalize_job_url

                url = normalize_job_url(j.get("url"), source=src) or (j.get("url") or "").strip()
                if url:
                    j["url"] = url
                key = url or f"{j.get('company_name')}|{j.get('title')}"
                if key in seen_urls:
                    continue
                seen_urls.add(key)
                combined.append(j)

        # Prefer freshest / keep cap for LLM
        return combined[: max(6, per * min(3, len(sources)))]

    async def discover_and_score_jobs(
        self, user_id: str, preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        logger.info(
            "Running multi-source JobDiscoveryAgent for user %s prefs=%s",
            user_id,
            preferences,
        )
        settings = get_settings()
        source_dir = Path(settings.RESUME_SOURCE_DIR)
        files = list_resume_files(source_dir)
        resume_text = extract_text(files[0].path)[:6000] if files else "No resume provided."

        target_roles = preferences.get("targetRoles", "")
        is_remote = preferences.get("isRemote", True)
        location_hubs = preferences.get("locationHubs", [])
        live_jobs = await self.fetch_live_jobs(target_roles, is_remote, location_hubs)
        source_meta = {str(j.get("id")): j for j in live_jobs}

        if not live_jobs:
            logger.warning("No live jobs found, falling back to AI synthesis.")
            jobs_context = "Generate 3 highly realistic, open job positions matching the preferences. Include a plausible https URL."
        else:
            formatted_jobs = []
            for j in live_jobs:
                clean_desc = clean_html(j.get("description", ""))[:1200]
                formatted_jobs.append(
                    f"ID: {j.get('id')}\n"
                    f"Title: {j.get('title')}\n"
                    f"Company: {j.get('company_name')}\n"
                    f"Location: {j.get('candidate_required_location', 'Remote')}\n"
                    f"Salary: {j.get('salary') or 'Competitive'}\n"
                    f"URL: {j.get('url')}\n"
                    f"Source: {j.get('source')}\n"
                    f"Posted: {j.get('publication_date')}\n"
                    f"Description: {clean_desc}\n"
                )
            jobs_context = (
                "Below are ACTUAL LIVE JOB POSTINGS from Remotive / RemoteOK / Vault Portals.\n"
                "You MUST use these exact jobs (keep ID, Company, Title, URL, Source).\n\n"
                + "\n---\n".join(formatted_jobs)
            )

        prompt = f"""
        You are an elite AI tech recruiter.
        User Preferences:
        {json.dumps(preferences, indent=2)}

        User Resume:
        {resume_text}

        Job Postings:
        {jobs_context}

        For each job:
        1. Keep exact Company, Title, Location, Salary, URL, Source, and ID when provided.
        2. matchScore 70-99 from resume fit.
        3. matchReason 1-2 sentences referencing resume skills.
        4. Short description summary.
        5. Extract `company_info` (1-2 sentences about the firm, if found).
        6. Extract `contact_info` (recruiter email or name, if found).
        7. Set posted_at from Posted when available.
        8. CRITICAL: If the job appears EXPIRED, CLOSED, or is older than 30 days, discard it immediately.
        """

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a job discovery engine. Output only the requested JSON. "
                    "Preserve real job URLs and IDs."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        def fallback():
            jobs = []
            seed = live_jobs[:3]
            if not seed:
                # No inventing dead links — empty discovery beats fake apply URLs
                return JobDiscoveryResponse(jobs=[])
            for j in seed:
                jobs.append(
                    DiscoveredJob(
                        id=str(j.get("id")),
                        company=j.get("company_name") or "Company",
                        title=j.get("title") or "Role",
                        location=j.get("candidate_required_location") or "Remote",
                        salary=j.get("salary") or "Competitive",
                        description=clean_html(j.get("description") or "")[:400],
                        matchScore=85,
                        matchReason="Strong match based on your preferences and resume stack.",
                        url=j.get("url"),
                        source=j.get("source"),
                        posted_at=j.get("publication_date"),
                    )
                )
            return JobDiscoveryResponse(jobs=jobs)

        result = await structured_generate(
            JobDiscoveryResponse, messages, fallback=fallback, max_tokens=3200
        )

        from app.application.services.job_urls import (
            clean_role_title,
            normalize_job_url,
        )

        jobs = []
        seen: set[str] = set()
        for job in result.jobs:
            dumped = job.model_dump()
            meta = source_meta.get(str(dumped.get("id"))) or {}
            source = dumped.get("source") or meta.get("source")
            # Prefer source-of-truth fields over LLM rewrite
            if meta.get("title"):
                dumped["title"] = clean_role_title(
                    meta.get("title"), dumped.get("title"), default="Open Role"
                )
            else:
                dumped["title"] = clean_role_title(
                    dumped.get("title"), default="Open Role"
                )
            if meta.get("company_name"):
                dumped["company"] = meta.get("company_name")
            url = normalize_job_url(
                dumped.get("url") or meta.get("url"), source=source
            )
            dumped["url"] = url
            dumped["source"] = source
            if not dumped.get("posted_at"):
                dumped["posted_at"] = meta.get("publication_date")
            if not dumped.get("id") or dumped["id"] == "string":
                dumped["id"] = f"job-live-{uuid.uuid4().hex[:6]}"
            # Skip unsourced / unusable rows (can't apply without URL + JD)
            desc = (dumped.get("description") or "").strip()
            if not url and len(desc) < 80:
                continue
            key = url or f"{dumped.get('company')}|{dumped.get('title')}"
            if key in seen:
                continue
            seen.add(key)
            dumped["applyable"] = bool(url)
            
            # Inject the raw description from the API as full_jd so UI can display it
            if meta.get("description"):
                dumped["full_jd"] = clean_html(meta.get("description", ""))
            else:
                dumped["full_jd"] = desc

            jobs.append(dumped)

        logger.info(
            "Scored %s applyable jobs from sources=%s",
            len(jobs),
            settings.job_discovery_source_list(),
        )
        return jobs
