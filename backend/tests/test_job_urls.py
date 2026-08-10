from app.application.services.job_urls import (
    clean_role_title,
    normalize_job_url,
)


def test_normalize_relative_remoteok():
    assert (
        normalize_job_url("/remote-jobs/123", "remoteok")
        == "https://remoteok.com/remote-jobs/123"
    )


def test_normalize_rejects_junk():
    assert normalize_job_url("null") is None
    assert normalize_job_url("none") is None
    assert normalize_job_url("") is None


def test_clean_fluff_role_title():
    assert clean_role_title("Great to see you apply!") == "Open Role"
    assert clean_role_title("Flutter Engineer") == "Flutter Engineer"
