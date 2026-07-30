"""
Job posting page scraper.

Prefers Playwright (renders JS-heavy ATS pages). Falls back to httpx + HTML
stripping when Playwright/Chromium is unavailable, then to a demo mock body.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

# Common containers on Greenhouse / Lever / Ashby / Workday / LinkedIn-ish pages
_CONTENT_SELECTORS = [
    "[data-testid='jobDescriptionText']",
    "[data-testid='job-description']",
    ".job-description",
    "#job-description",
    ".jobsearch-JobComponent-description",
    "[class*='job-description']",
    "[class*='JobDescription']",
    "article",
    "main",
    "[role='main']",
]

_TITLE_SELECTORS = [
    "h1",
    "[data-testid='jobsearch-JobInfoHeader-title']",
    ".job-title",
    "[class*='job-title']",
]


@dataclass
class ScrapeResult:
    url: str
    text: str
    title: Optional[str] = None
    company: Optional[str] = None
    source: str = "mock"  # playwright | httpx | mock
    error: Optional[str] = None


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", html)
    html = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", html)
    html = re.sub(r"(?is)<noscript[^>]*>.*?</noscript>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&#39;", "'", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _meta_content(html: str, prop: str) -> Optional[str]:
    patterns = [
        rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(prop)}["\']',
        rf'<meta[^>]+name=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
        rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(prop)}["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, flags=re.I)
        if m:
            return m.group(1).strip()
    return None


def _json_ld_job(html: str) -> dict[str, Any]:
    for m in re.finditer(
        r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
    ):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if not isinstance(item, dict):
                continue
            t = item.get("@type")
            types = t if isinstance(t, list) else [t]
            if any(str(x).lower() == "jobposting" for x in types if x):
                return item
    return {}


def _hints_from_html(html: str, url: str) -> tuple[Optional[str], Optional[str], str]:
    ld = _json_ld_job(html)
    title = ld.get("title") if isinstance(ld.get("title"), str) else None
    company = None
    org = ld.get("hiringOrganization")
    if isinstance(org, dict) and isinstance(org.get("name"), str):
        company = org["name"]
    elif isinstance(org, str):
        company = org

    title = title or _meta_content(html, "og:title") or _meta_content(html, "twitter:title")
    company = company or _meta_content(html, "og:site_name")

    desc = ""
    if isinstance(ld.get("description"), str):
        desc = _strip_html(ld["description"])
    # Prefer JSON-LD text; only fall back to page body if LD desc is empty.
    # (Stripping the full HTML removes <script type="ld+json">, so short LD
    # descriptions must not be overwritten with an empty body.)
    if not desc:
        desc = _strip_html(html)
    elif len(desc) < 80:
        page_text = _strip_html(html)
        if len(page_text) > len(desc):
            desc = page_text

    if not company:
        host = urlparse(url).hostname or ""
        company = host.replace("www.", "").split(".")[0].title() or None

    return title, company, desc


def _mock_body(url: str) -> ScrapeResult:
    host = urlparse(url).hostname or "example.com"
    company = host.replace("www.", "").split(".")[0].title()
    text = (
        f"Software Engineer at {company}\n\n"
        f"Source URL: {url}\n\n"
        "We are hiring a Software Engineer to build backend services with Python, "
        "FastAPI, PostgreSQL, Docker, and AWS. Nice to have: LangGraph, Redis, Qdrant.\n\n"
        "Responsibilities:\n"
        "- Design and implement APIs\n"
        "- Write tests and observability hooks\n"
        "- Collaborate with product on career tooling\n\n"
        "Benefits: Health insurance, remote work, 401k.\n"
        "(Demo scrape — Playwright/Chromium unavailable or page blocked.)"
    )
    return ScrapeResult(
        url=url,
        text=text,
        title="Software Engineer",
        company=company,
        source="mock",
        error="Playwright/httpx scrape unavailable; using demo body",
    )


async def _scrape_httpx(url: str) -> ScrapeResult:
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=25.0,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; CareerOS/1.0; +https://localhost) "
                "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
        },
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

    title, company, text = _hints_from_html(html, url)
    if len(text) < 40:
        raise ValueError("Fetched page had too little text")
    return ScrapeResult(
        url=url,
        text=text[:50000],
        title=title,
        company=company,
        source="httpx",
    )


async def _scrape_playwright(url: str) -> ScrapeResult:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass

            title = None
            for sel in _TITLE_SELECTORS:
                loc = page.locator(sel).first
                if await loc.count():
                    title = (await loc.inner_text()).strip() or None
                    if title:
                        break

            body = ""
            for sel in _CONTENT_SELECTORS:
                loc = page.locator(sel).first
                if await loc.count():
                    body = (await loc.inner_text()).strip()
                    if len(body) > 80:
                        break

            if len(body) < 80:
                body = (await page.locator("body").inner_text()).strip()

            html = await page.content()
            html_title, company, _ = _hints_from_html(html, url)
            title = title or html_title
        finally:
            await browser.close()

    if len(body) < 40:
        raise ValueError("Playwright extracted too little text")

    return ScrapeResult(
        url=url,
        text=body[:50000],
        title=title,
        company=company,
        source="playwright",
    )


async def scrape_job_page(url: str) -> ScrapeResult:
    """
    Scrape a job posting URL. Order: Playwright → httpx → mock.
    Never raises; always returns usable text for the intake agent.
    """
    errors: list[str] = []

    try:
        return await _scrape_playwright(url)
    except Exception as exc:
        errors.append(f"playwright: {exc}")

    try:
        return await _scrape_httpx(url)
    except Exception as exc:
        errors.append(f"httpx: {exc}")

    mock = _mock_body(url)
    mock.error = "; ".join(errors) if errors else mock.error
    return mock
