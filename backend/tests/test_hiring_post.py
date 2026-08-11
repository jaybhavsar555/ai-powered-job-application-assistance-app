"""Unit tests for LinkedIn / hiring-post paste parser."""

from app.application.services.hiring_post import parse_hiring_post, build_interest_email

SAMPLE = """
Immediate Hiring | Mobile App Developer

We are looking for a talented Mobile App Developer to join our team.

Location: USA
Employment Type: Full-Time | W2 | C2C | Contract

Required Skills:
• Flutter or React Native
• Android (Java/Kotlin) and/or iOS (Swift)
• REST API Integration

Interested candidates can share their updated resume at:
sadafshabbir230@gmail.com

#MobileAppDeveloper #Flutter #HiringNow
"""

SOURCE = (
    "https://www.linkedin.com/posts/sadaf-shabbir-87a147214_"
    "juniordataanalyst-mobileappdeveloper-flutter-share-7492949379830521856-jqHA/"
    "?utm_source=share"
)


def test_parse_extracts_email_and_role():
    p = parse_hiring_post(SAMPLE, source_url=SOURCE)
    assert p.contact_email == "sadafshabbir230@gmail.com"
    assert "Mobile" in p.role_title or "App" in p.role_title
    assert p.linkedin_post_url and "linkedin.com/posts" in p.linkedin_post_url
    assert "utm_source" not in (p.linkedin_post_url or "")
    assert p.linkedin_profile_url and "sadaf-shabbir" in p.linkedin_profile_url
    assert any("Flutter" in s or "React" in s for s in p.required_skills)


def test_parse_short_text_raises():
    try:
        parse_hiring_post("hi")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_interest_email_mentions_role():
    subj, body = build_interest_email(
        contact_name="Sadaf Shabbir",
        role_title="Mobile App Developer",
        company_name="LinkedIn hiring post",
        candidate_name="Jay Bhavsar",
        highlight_skills=["Flutter", "React Native"],
    )
    assert "Mobile App Developer" in subj or "Mobile App Developer" in body
    assert "Flutter" in body
    assert "Hi Sadaf" in body
