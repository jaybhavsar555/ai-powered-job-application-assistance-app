"""Multi-source job discovery: Vault job_portal KBs first, then remote boards."""

from __future__ import annotations

import logging
import re
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

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
    company_info: Optional[str] = Field(
        default=None, description="A brief blurb about the hiring firm extracted from the JD"
    )
    contact_info: Optional[str] = Field(
        default=None, description="Any recruiter name or email found in the JD"
    )
    full_jd: Optional[str] = Field(
        default=None, description="The full raw job description (populated server-side)"
    )
    url: Optional[str] = Field(default=None, description="Canonical job posting URL")
    source: Optional[str] = Field(
        default=None, description="vault_portals|remotive|remoteok|arbeitnow"
    )
    posted_at: Optional[str] = Field(default=None, description="ISO date if known")


class JobDiscoveryResponse(BaseModel):
    jobs: List[DiscoveredJob]


def clean_html(raw_html: str) -> str:
    try:
        from bs4 import BeautifulSoup

        return BeautifulSoup(raw_html or "", "html.parser").get_text(
            separator=" ", strip=True
        )
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


def _portal_host(url: str) -> str:
    import urllib.parse

    host = (urllib.parse.urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


class JobDiscoveryAgent:
    def __init__(self, llm_service=None, knowledge_service=None):
        self.llm = llm_service
        self.knowledge = knowledge_service

    async def load_vault_portal_sites(self, user_id: str) -> List[Dict[str, str]]:
        """Load job_portal entities from Vault KBs; fall back to curated list."""
        from app.core.job_portals import JOB_PORTALS

        portals: List[Dict[str, str]] = []
        if self.knowledge is not None and user_id:
            try:
                entities = await self.knowledge.get_by_user_id(UUID(user_id))
                for e in entities:
                    if getattr(e, "entity_type", None) != "job_portal":
                        continue
                    content = e.content or {}
                    url = content.get("url")
                    if not isinstance(url, str) or not url.startswith("http"):
                        continue
                    portals.append(
                        {
                            "title": e.title or "Job Portal",
                            "url": url,
                            "region": str(content.get("region") or "Global"),
                        }
                    )
            except Exception as exc:
                logger.warning("Could not load Vault job_portal KBs: %s", exc)

        if portals:
            seen: set[str] = set()
            unique: List[Dict[str, str]] = []
            for p in portals:
                host = _portal_host(p["url"])
                if not host or host in seen:
                    continue
                seen.add(host)
                unique.append(p)
            logger.info("Discovery using %d Vault job_portal sites", len(unique))
            return unique

        logger.info("No Vault job_portal KBs — using curated JOB_PORTALS fallback")
        return [
            {
                "title": p["title"],
                "url": p["url"],
                "region": p.get("region", "Global"),
            }
            for p in JOB_PORTALS
        ]

    async def fetch_remotive(self, search_term: str, limit: int) -> List[Dict[str, Any]]:
        url = f"https://remotive.com/api/remote-jobs?search={search_term}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                jobs = resp.json().get("jobs") or []
                out: List[Dict[str, Any]] = []
                for j in jobs[:limit]:
                    out.append(
                        {
                            "id": f"remotive-{j.get('id')}",
                            "title": j.get("title") or "Role",
                            "company_name": j.get("company_name") or "Company",
                            "candidate_required_location": j.get(
                                "candidate_required_location"
                            )
                            or "Remote",
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
        url = "https://remoteok.com/api"
        try:
            async with httpx.AsyncClient(
                timeout=20.0,
                headers={"User-Agent": "CareerOS/1.0"},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                rows = resp.json()
                if not isinstance(rows, list):
                    return []
                term = (search_term or "").lower()
                out: List[Dict[str, Any]] = []
                for j in rows:
                    if not isinstance(j, dict) or not j.get("id"):
                        continue
                    blob = " ".join(
                        [
                            str(j.get("position") or ""),
                            str(j.get("company") or ""),
                            " ".join(j.get("tags") or []),
                            str(j.get("description") or "")[:400],
                        ]
                    ).lower()
                    if term and term not in blob:
                        continue
                    out.append(
                        {
                            "id": f"remoteok-{j.get('id')}",
                            "title": j.get("position") or "Role",
                            "company_name": j.get("company") or "Company",
                            "candidate_required_location": "Remote",
                            "salary": (
                                f"${j.get('salary_min')}-${j.get('salary_max')}"
                                if j.get("salary_min")
                                else "Competitive"
                            ),
                            "url": j.get("url") or j.get("apply_url"),
                            "description": j.get("description") or "",
                            "publication_date": _iso_from_epoch(
                                j.get("date") or j.get("epoch")
                            ),
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
            params: Dict[str, Any] = {"page": 1}
            if search_term:
                params["search"] = search_term
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    "https://www.arbeitnow.com/api/job-board-api", params=params
                )
                resp.raise_for_status()
                data = resp.json().get("data") or []
                out: List[Dict[str, Any]] = []
                for j in data[:limit]:
                    out.append(
                        {
                            "id": f"arbeitnow-{j.get('slug') or j.get('url')}",
                            "title": j.get("title") or "Role",
                            "company_name": j.get("company_name") or "Company",
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

    async def fetch_wwr_rss(self, search_term: str, limit: int) -> List[Dict[str, Any]]:
        """We Work Remotely programming RSS — used when WWR is in Vault portals."""
        feeds = [
            "https://weworkremotely.com/categories/remote-programming-jobs.rss",
            "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
        ]
        term = (search_term or "").lower()
        out: List[Dict[str, Any]] = []
        seen: set[str] = set()
        try:
            async with httpx.AsyncClient(
                timeout=20.0,
                follow_redirects=True,
                headers={"User-Agent": "CareerOS/1.0"},
            ) as client:
                for feed in feeds:
                    if len(out) >= limit:
                        break
                    try:
                        resp = await client.get(feed)
                        if resp.status_code != 200:
                            continue
                        from bs4 import BeautifulSoup

                        soup = BeautifulSoup(resp.text, "xml")
                        for item in soup.find_all("item"):
                            if len(out) >= limit:
                                break
                            title = (item.title.get_text(strip=True) if item.title else "") or "Role"
                            link = (item.link.get_text(strip=True) if item.link else "") or ""
                            desc = (
                                item.description.get_text(strip=True) if item.description else ""
                            )
                            blob = f"{title} {desc}".lower()
                            if term and term not in blob and not any(
                                t in blob for t in term.split() if len(t) > 3
                            ):
                                continue
                            if not link or link in seen:
                                continue
                            seen.add(link)
                            company = "We Work Remotely"
                            if ":" in title:
                                # Common WWR format: "Company: Role"
                                parts = title.split(":", 1)
                                company = parts[0].strip() or company
                                title = parts[1].strip() or title
                            out.append(
                                {
                                    "id": f"wwr-{abs(hash(link)) % 10_000_000}",
                                    "title": title[:160],
                                    "company_name": company,
                                    "candidate_required_location": "Remote",
                                    "salary": "Competitive",
                                    "url": link,
                                    "description": clean_html(desc)[:1200],
                                    "publication_date": None,
                                    "source": "vault_portals",
                                }
                            )
                    except Exception as feed_exc:
                        logger.warning("WWR feed %s failed: %s", feed, feed_exc)
        except Exception as e:
            logger.error("WWR RSS fetch failed: %s", e)
            return []
        return out[:limit]

    async def _ddg_portal_batch(
        self,
        portals: List[Dict[str, str]],
        search_term: str,
        location: str,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """DuckDuckGo HTML/Lite search restricted to a batch of Vault portal hosts."""
        import urllib.parse
        from bs4 import BeautifulSoup

        hosts = [_portal_host(p["url"]) for p in portals if p.get("url")]
        hosts = [h for h in hosts if h]
        if not hosts:
            return []

        site_str = " OR ".join([f"site:{h}" for h in hosts])
        loc = (location or "Remote").strip()
        query = f'({site_str}) "{search_term}"'
        if loc and loc.lower() not in ("remote", "any"):
            query += f' "{loc}"'
        encoded = urllib.parse.quote(query)
        urls = [
            f"https://html.duckduckgo.com/html/?q={encoded}&df=m",
            f"https://lite.duckduckgo.com/lite/?q={encoded}",
        ]

        title_by_host = {
            _portal_host(p["url"]): p.get("title") or "Portal" for p in portals
        }

        try:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/html,application/xhtml+xml",
                },
                follow_redirects=True,
                timeout=15.0,
            ) as client:
                for url in urls:
                    try:
                        response = await client.get(url)
                    except Exception:
                        continue
                    if response.status_code != 200:
                        continue
                    soup = BeautifulSoup(response.text, "html.parser")
                    result_links = soup.select("a.result__a")
                    if not result_links:
                        result_links = soup.select("a.result__url")
                    if not result_links:
                        # DuckDuckGo lite
                        result_links = soup.select("a.result-link") or soup.select(
                            "td a[href^='http']"
                        )
                    snippets = soup.select("a.result__snippet") or soup.select(
                        ".result__snippet"
                    )

                    out: List[Dict[str, Any]] = []
                    for i, a in enumerate(result_links):
                        if len(out) >= limit:
                            break
                        link = a.get("href") or ""
                        if "uddg=" in link:
                            link = urllib.parse.unquote(
                                link.split("uddg=")[1].split("&")[0]
                            )
                        elif link.startswith("//"):
                            link = "https:" + link
                        elif link.startswith("/"):
                            continue
                        if not link.startswith("http"):
                            continue
                        # Skip DDG internal / tracking
                        if "duckduckgo.com" in link:
                            continue

                        host = _portal_host(link)
                        if host and not any(
                            host == h or host.endswith("." + h) for h in hosts
                        ):
                            continue

                        title = (a.get_text(strip=True) or "").strip()
                        if not title or title.startswith("http"):
                            title = (
                                f"{search_term.title()} — "
                                f"{title_by_host.get(host, host)}"
                            )
                        snippet = ""
                        if i < len(snippets):
                            snippet = snippets[i].get_text(strip=True)

                        portal_name = title_by_host.get(host) or host or "Vault Portal"
                        out.append(
                            {
                                "id": f"vault-{abs(hash(link)) % 10_000_000}",
                                "title": title[:160],
                                "company_name": portal_name,
                                "candidate_required_location": location
                                or "Hybrid/Remote",
                                "salary": "Competitive",
                                "url": link,
                                "description": snippet
                                or f"Opening found via Vault portal {portal_name}",
                                "publication_date": None,
                                "source": "vault_portals",
                            }
                        )
                    if out:
                        return out
                return []
        except Exception as e:
            logger.error("Vault portal DDG batch failed: %s", e)
            return []

    async def fetch_vault_portals(
        self,
        search_term: str,
        location: str,
        limit: int,
        portals: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search using every Vault job_portal KB site.

        Portals with known feeds/APIs (Remotive, RemoteOK, Arbeitnow, WWR) are
        fetched directly; remaining hosts go through DuckDuckGo site: filters.
        """
        from app.core.job_portals import JOB_PORTALS

        portal_list = portals or [
            {
                "title": p["title"],
                "url": p["url"],
                "region": p.get("region", "Global"),
            }
            for p in JOB_PORTALS
        ]
        if not portal_list:
            return []

        # Host → dedicated fetcher (returns rows already shaped)
        api_hosts = {
            "remotive.com": lambda: self.fetch_remotive(search_term, max(3, limit // 3)),
            "remoteok.com": lambda: self.fetch_remoteok(search_term, max(3, limit // 3)),
            "arbeitnow.com": lambda: self.fetch_arbeitnow(
                search_term, max(3, limit // 3)
            ),
            "weworkremotely.com": lambda: self.fetch_wwr_rss(
                search_term, max(3, limit // 3)
            ),
        }

        combined: List[Dict[str, Any]] = []
        seen: set[str] = set()
        ddg_portals: List[Dict[str, str]] = []

        for p in portal_list:
            host = _portal_host(p.get("url") or "")
            fetcher = api_hosts.get(host)
            if fetcher:
                try:
                    rows = await fetcher()
                except Exception as exc:
                    logger.warning("Vault API/RSS for %s failed: %s", host, exc)
                    rows = []
                for row in rows:
                    # Keep original board source when useful, but mark vault-driven
                    row = dict(row)
                    if row.get("source") in ("remotive", "remoteok", "arbeitnow"):
                        # Leave source as-is so UI still shows board — still vault-driven
                        pass
                    else:
                        row["source"] = "vault_portals"
                    key = (row.get("url") or "").rstrip("/").lower()
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    combined.append(row)
                    if len(combined) >= limit:
                        break
            else:
                ddg_portals.append(p)
            if len(combined) >= limit:
                break

        # DuckDuckGo for portals without APIs (Instahyre, Wellfound, YC, …)
        if len(combined) < limit and ddg_portals:
            need = limit - len(combined)
            batch_size = 4
            batches = [
                ddg_portals[i : i + batch_size]
                for i in range(0, len(ddg_portals), batch_size)
            ]
            per_batch = max(2, (need + len(batches) - 1) // max(1, len(batches)))
            for batch in batches:
                if len(combined) >= limit:
                    break
                rows = await self._ddg_portal_batch(
                    batch, search_term, location, per_batch
                )
                for row in rows:
                    key = (row.get("url") or "").rstrip("/").lower()
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    combined.append(row)
                    if len(combined) >= limit:
                        break

        logger.info(
            "Vault portal search: %d portals (%d API/RSS-capable, %d DDG) → %d hits",
            len(portal_list),
            len(portal_list) - len(ddg_portals),
            len(ddg_portals),
            len(combined),
        )
        return combined[:limit]

    async def fetch_live_jobs(
        self,
        target_roles: str,
        is_remote: bool,
        location_hubs: list[str],
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        settings = get_settings()
        search_term = (
            target_roles.split(",")[0].strip() if target_roles else "software engineer"
        )
        location = (
            "Remote" if is_remote else (location_hubs[0] if location_hubs else "Hybrid")
        )
        board_limit = max(2, int(settings.JOB_DISCOVERY_PER_SOURCE or 3))
        vault_limit = max(
            5, int(getattr(settings, "JOB_DISCOVERY_VAULT_LIMIT", 12) or 12)
        )
        max_results = max(
            8, int(getattr(settings, "JOB_DISCOVERY_MAX_RESULTS", 15) or 15)
        )
        sources = settings.job_discovery_source_list() or [
            "vault_portals",
            "remotive",
            "remoteok",
            "arbeitnow",
        ]

        vault_sites: List[Dict[str, str]] = []
        if "vault_portals" in sources:
            vault_sites = await self.load_vault_portal_sites(user_id or "")

        combined: List[Dict[str, Any]] = []
        seen_urls: set[str] = set()

        fetchers = {
            "remotive": lambda term, lim: self.fetch_remotive(term, lim),
            "remoteok": lambda term, lim: self.fetch_remoteok(term, lim),
            "arbeitnow": lambda term, lim: self.fetch_arbeitnow(term, lim),
            "vault_portals": lambda term, lim: self.fetch_vault_portals(
                term, location, lim, portals=vault_sites
            ),
        }
        # Vault KBs first, then remote API boards as fill
        ordered = [s for s in sources if s == "vault_portals"] + [
            s for s in sources if s != "vault_portals"
        ]
        for src in ordered:
            fn = fetchers.get(src)
            if not fn:
                continue
            lim = vault_limit if src == "vault_portals" else board_limit
            try:
                batch = await fn(search_term, lim)
            except Exception as e:
                logger.error("Source %s failed: %s", src, e)
                batch = []
            for j in batch:
                from app.application.services.job_urls import normalize_job_url

                url = normalize_job_url(j.get("url"), source=src) or (
                    j.get("url") or ""
                ).strip()
                if url:
                    j["url"] = url
                key = url or f"{j.get('company_name')}|{j.get('title')}"
                if key in seen_urls:
                    continue
                seen_urls.add(key)
                combined.append(j)

        # Prefer Vault portal hits; fill remaining slots from remote boards
        vault = [j for j in combined if j.get("source") == "vault_portals"]
        boards = [j for j in combined if j.get("source") != "vault_portals"]
        keep_vault = min(len(vault), max_results)
        keep_boards = max(0, max_results - keep_vault)
        out = vault[:keep_vault] + boards[:keep_boards]
        return out[:max_results]

    async def discover_and_score_jobs(
        self, user_id: str, preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        logger.info(
            "Running Vault-first JobDiscoveryAgent for user %s prefs=%s",
            user_id,
            preferences,
        )
        settings = get_settings()
        source_dir = Path(settings.RESUME_SOURCE_DIR)
        files = list_resume_files(source_dir)
        resume_text = (
            extract_text(files[0].path)[:6000] if files else "No resume provided."
        )

        target_roles = preferences.get("targetRoles", "")
        is_remote = preferences.get("isRemote", True)
        location_hubs = preferences.get("locationHubs", [])
        live_jobs = await self.fetch_live_jobs(
            target_roles, is_remote, location_hubs, user_id=user_id
        )
        source_meta = {str(j.get("id")): j for j in live_jobs}

        if not live_jobs:
            logger.warning(
                "No live jobs from Vault portals / Remotive / RemoteOK / Arbeitnow — empty."
            )
            return []
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
            "Below are ACTUAL LIVE JOB POSTINGS primarily from your Vault job_portal "
            "KBs (Instahyre, Wellfound, YC, WWR, …), with Remotive / RemoteOK / "
            "Arbeitnow used only to fill remaining slots.\n"
            "You MUST use these exact jobs (keep ID, Company, Title, URL, Source).\n"
            f"Score and return up to {getattr(settings, 'JOB_DISCOVERY_MAX_RESULTS', 15)} jobs.\n\n"
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
            seed = live_jobs[: max(3, min(15, len(live_jobs)))]
            if not seed:
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
                        matchScore=78,
                        matchReason=(
                            "Vault/portal match (LLM scoring unavailable — "
                            "scores are preference-heuristic; re-run when Token Harbor is free)."
                        ),
                        url=j.get("url"),
                        source=j.get("source"),
                        posted_at=j.get("publication_date"),
                    )
                )
            return JobDiscoveryResponse(jobs=jobs)

        try:
            result = await structured_generate(
                JobDiscoveryResponse, messages, fallback=None, max_tokens=1600
            )
        except RuntimeError as exc:
            logger.warning(
                "LLM discovery score failed — using live board heuristic: %s", exc
            )
            result = fallback()

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
            desc = (dumped.get("description") or "").strip()
            if not url and len(desc) < 80:
                continue
            key = url or f"{dumped.get('company')}|{dumped.get('title')}"
            if key in seen:
                continue
            seen.add(key)
            jobs.append(dumped)

        if not jobs and live_jobs:
            return fallback().model_dump()["jobs"]
        return jobs[
            : max(8, int(getattr(settings, "JOB_DISCOVERY_MAX_RESULTS", 15) or 15))
        ]
