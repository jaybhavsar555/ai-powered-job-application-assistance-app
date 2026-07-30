import pytest

from app.infrastructure.scraping.job_page import (
    _hints_from_html,
    _mock_body,
    _strip_html,
    scrape_job_page,
)


def test_strip_html_removes_tags():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"


def test_hints_from_json_ld():
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@type":"JobPosting","title":"Backend Engineer",
     "hiringOrganization":{"name":"Acme"},
     "description":"<p>Build APIs with Python and FastAPI.</p>"}
    </script>
    </head><body></body></html>
    """
    title, company, text = _hints_from_html(html, "https://jobs.acme.com/1")
    assert title == "Backend Engineer"
    assert company == "Acme"
    assert "Python" in text


def test_mock_body_has_content():
    result = _mock_body("https://boards.greenhouse.io/demo/jobs/1")
    assert result.source == "mock"
    assert "Software Engineer" in result.text
    assert result.company


@pytest.mark.asyncio
async def test_scrape_falls_back_without_raising():
    # Invalid / blocked host should still return mock text
    result = await scrape_job_page("https://this-host-should-not-resolve.invalid/job/1")
    assert result.text
    assert result.source in {"playwright", "httpx", "mock"}
