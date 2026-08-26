"""Job portal catalog — major boards used for Vault seeding."""

from app.core.job_portals import JOB_PORTALS, is_ats_host


def test_major_boards_include_linkedin_indeed_unstop():
    titles = {p["title"] for p in JOB_PORTALS}
    assert "LinkedIn Jobs" in titles
    assert "Indeed" in titles
    assert "Unstop" in titles
    assert "Instahyre" in titles
    assert "Wellfound" in titles


def test_major_board_category():
    majors = [p for p in JOB_PORTALS if p.get("category") == "major_board"]
    urls = {p["url"] for p in majors}
    assert any("linkedin.com" in u for u in urls)
    assert any("indeed.com" in u for u in urls)
    assert any("unstop.com" in u for u in urls)


def test_ats_host_detection():
    assert is_ats_host("https://boards.greenhouse.io/acme")
    assert is_ats_host("jobs.lever.co")
    assert not is_ats_host("https://www.linkedin.com/jobs/")
