import pytest

from app.infrastructure.scraping.company_research import (
    _failed_signals,
    _guess_homepage,
    gather_company_signals,
)


def test_guess_homepage_skips_ats():
    url = _guess_homepage("Acme", "https://boards.greenhouse.io/acme/jobs/1")
    assert url is None or "greenhouse" not in url


def test_guess_homepage_from_company_site_job():
    url = _guess_homepage("Acme", "https://careers.acme.com/jobs/1")
    assert url == "https://careers.acme.com"


def test_failed_signals_empty():
    s = _failed_signals("Acme", ["site: timeout"])
    assert s.source == "failed"
    assert not (s.raw_text or "").strip()
    assert "Acme" in s.company_name
    assert s.error


@pytest.mark.asyncio
async def test_gather_never_raises():
    result = await gather_company_signals("Acme Robotics", None)
    assert result.source in {"site", "serp", "failed"}
    if result.source == "failed":
        assert not (result.raw_text or "").strip()
        assert result.error
