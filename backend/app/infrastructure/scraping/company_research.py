"""
Lightweight company signal gathering for the Company Research agent.

Tries: (1) company site from job URL host, (2) DuckDuckGo HTML snippets.
On total failure returns empty raw_text with source=failed — never invents blurbs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import quote_plus, urlparse

import httpx

from app.infrastructure.scraping.job_page import _strip_html


@dataclass
class CompanySignals:
    company_name: str
    raw_text: str
    sources: List[str] = field(default_factory=list)
    source: str = "failed"  # site | serp | failed
    error: Optional[str] = None


_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _guess_homepage(company: str, job_url: Optional[str]) -> Optional[str]:
    if job_url:
        host = (urlparse(job_url).hostname or "").lower()
        # Skip known ATS hosts — they are not the company site
        ats = (
            "greenhouse.io",
            "lever.co",
            "ashbyhq.com",
            "myworkdayjobs.com",
            "linkedin.com",
            "indeed.com",
            "boards.eu",
        )
        if host and not any(a in host for a in ats):
            return f"https://{host}"
    slug = re.sub(r"[^a-z0-9]", "", (company or "").lower())
    if len(slug) >= 3:
        return f"https://www.{slug}.com"
    return None


async def _fetch_text(url: str, client: httpx.AsyncClient) -> str:
    resp = await client.get(url)
    resp.raise_for_status()
    text = _strip_html(resp.text)
    return text[:12000]


async def _fetch_serp_snippets(company: str, client: httpx.AsyncClient) -> str:
    q = quote_plus(f"{company} company funding products technology")
    url = f"https://html.duckduckgo.com/html/?q={q}"
    resp = await client.get(url)
    resp.raise_for_status()
    # DuckDuckGo result snippets
    snippets = re.findall(
        r'class="result__snippet"[^>]*>(.*?)</(?:a|td|div)',
        resp.text,
        flags=re.I | re.S,
    )
    if not snippets:
        snippets = re.findall(r'class="result__a"[^>]*>(.*?)</a>', resp.text, flags=re.I | re.S)
    cleaned = [_strip_html(s) for s in snippets[:8]]
    cleaned = [c for c in cleaned if len(c) > 40]
    if not cleaned:
        raise ValueError("No SERP snippets")
    return "\n\n".join(cleaned)[:8000]


def _failed_signals(company: str, errors: list[str]) -> CompanySignals:
    name = company or "Unknown Company"
    return CompanySignals(
        company_name=name,
        raw_text="",
        sources=[],
        source="failed",
        error=(
            "; ".join(errors)
            if errors
            else "Live company research unavailable — no invented company blurb."
        ),
    )


async def gather_company_signals(
    company: str,
    job_url: Optional[str] = None,
) -> CompanySignals:
    errors: list[str] = []
    name = (company or "").strip() or "Unknown Company"

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=8.0,
        headers={"User-Agent": _UA, "Accept": "text/html"},
    ) as client:
        homepage = _guess_homepage(name, job_url)
        if homepage:
            try:
                text = await _fetch_text(homepage, client)
                if len(text) > 120:
                    about = homepage.rstrip("/") + "/about"
                    try:
                        extra = await _fetch_text(about, client)
                        if len(extra) > 80:
                            text = f"{text}\n\n{extra}"
                    except Exception:
                        pass
                    return CompanySignals(
                        company_name=name,
                        raw_text=text[:12000],
                        sources=[homepage],
                        source="site",
                    )
            except Exception as exc:
                errors.append(f"site: {exc}")

        try:
            serp = await _fetch_serp_snippets(name, client)
            return CompanySignals(
                company_name=name,
                raw_text=serp,
                sources=[f"duckduckgo://{name}"],
                source="serp",
            )
        except Exception as exc:
            errors.append(f"serp: {exc}")

    return _failed_signals(name, errors)
