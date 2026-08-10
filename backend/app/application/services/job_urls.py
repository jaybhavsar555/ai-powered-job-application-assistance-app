"""Normalize and validate job posting URLs for discovery + wishlist ingest."""

from __future__ import annotations

from typing import Optional
from urllib.parse import urljoin, urlparse

_SOURCE_BASES = {
    "remoteok": "https://remoteok.com",
    "remotive": "https://remotive.com",
    "arbeitnow": "https://www.arbeitnow.com",
}

_FLUFF = (
    "great to see",
    "work together",
    "join us",
    "we're hiring",
    "apply now",
    "thank you",
    "looking forward",
)


def looks_like_role_title(title: Optional[str]) -> bool:
    t = (title or "").strip()
    if not t or len(t) > 80:
        return False
    low = t.lower()
    return not any(x in low for x in _FLUFF)


def clean_role_title(
    title: Optional[str],
    *fallbacks: Optional[str],
    default: str = "Open Role",
) -> str:
    for candidate in (title, *fallbacks):
        if looks_like_role_title(candidate):
            return str(candidate).strip()
    return default


def normalize_job_url(
    url: Optional[str],
    source: Optional[str] = None,
) -> Optional[str]:
    raw = (url or "").strip()
    if not raw or raw.lower() in {"null", "none", "undefined", "n/a"}:
        return None

    src = (source or "").strip().lower()
    if raw.startswith("/") and src in _SOURCE_BASES:
        raw = urljoin(_SOURCE_BASES[src] + "/", raw.lstrip("/"))
    elif raw.startswith("//"):
        raw = "https:" + raw
    elif not raw.lower().startswith(("http://", "https://")):
        # Bare host/path from scrapers
        if "." in raw.split("/")[0]:
            raw = "https://" + raw.lstrip("/")
        elif src in _SOURCE_BASES:
            raw = urljoin(_SOURCE_BASES[src] + "/", raw.lstrip("/"))
        else:
            return None

    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    # Drop obvious junk
    if parsed.netloc.lower() in {"example.com", "localhost"}:
        return None
    return raw


def is_applyable_url(url: Optional[str]) -> bool:
    return bool(normalize_job_url(url))
