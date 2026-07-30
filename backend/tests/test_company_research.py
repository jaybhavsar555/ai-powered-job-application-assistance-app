import pytest

from app.infrastructure.scraping.company_research import (
    _guess_homepage,
    _mock_signals,
    gather_company_signals,
)


def test_guess_homepage_skips_ats():
    url = _guess_homepage("Acme", "https://boards.greenhouse.io/acme/jobs/1")
    assert url is None or "greenhouse" not in url


def test_guess_homepage_from_company_site_job():
    url = _guess_homepage("Acme", "https://careers.acme.com/jobs/1")
    assert url == "https://careers.acme.com"


def test_mock_signals():
    s = _mock_signals("Acme")
    assert s.source == "mock"
    assert "Acme" in s.raw_text


@pytest.mark.asyncio
async def test_gather_never_raises():
    result = await gather_company_signals("Acme Robotics", None)
    assert result.raw_text
    assert result.source in {"site", "serp", "mock"}
