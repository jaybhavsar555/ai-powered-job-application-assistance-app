"""Parse hiring posts (LinkedIn paste, email blasts) into structured apply targets."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import urlparse, parse_qs, urlunparse


_EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![A-Za-z0-9._%+-])"
)
_LINKEDIN_POST_RE = re.compile(
    r"https?://(?:www\.)?linkedin\.com/(?:posts|feed/update)/[^\s<>\"']+",
    re.I,
)
_LINKEDIN_PROFILE_RE = re.compile(
    r"https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?",
    re.I,
)


@dataclass
class ParsedHiringPost:
    role_title: str
    company_name: str
    description: str
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    linkedin_post_url: Optional[str] = None
    linkedin_profile_url: Optional[str] = None
    required_skills: List[str] = field(default_factory=list)
    location: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


def _clean_linkedin_url(url: str) -> str:
    parsed = urlparse(url.strip().rstrip(").,]\""))
    # Drop tracking query params
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _guess_role(text: str) -> str:
    patterns = [
        r"(?i)(?:hiring|looking for|seeking|need(?:ed)?)\s+(?:an?\s+)?([^\n|]{8,80}?)(?:\s*[|\n]|$)",
        r"(?i)^(?:🚀\s*)?(?:immediate hiring\s*[|–—-]\s*)?([^\n]{8,80})",
        r"(?i)(?:role|position|title)\s*[:\-]\s*([^\n]{5,80})",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            role = re.sub(r"[#|📢🚀📍💼⏳🔹⭐📩⚡]+", "", m.group(1)).strip(" -–—|")
            role = re.sub(r"\s+", " ", role)
            if 4 < len(role) < 80 and "resume" not in role.lower():
                return role
    # Hashtag fallback
    for tag in ("MobileAppDeveloper", "Flutter", "ReactNative", "AndroidDeveloper"):
        if tag.lower() in text.lower().replace(" ", ""):
            return re.sub(r"([a-z])([A-Z])", r"\1 \2", tag)
    return "Open Role"


def _guess_contact_name(text: str, email: Optional[str]) -> Optional[str]:
    # "share their updated resume at" posts often don't include a name in body
    m = re.search(r"(?i)(?:from|posted by|contact)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", text)
    if m:
        return m.group(1).strip()
    if email:
        local = email.split("@")[0]
        # sadafshabbir230 → Sadaf Shabbir (best-effort)
        letters = re.sub(r"\d+", "", local)
        if len(letters) >= 4:
            # split camel / glued names poorly — capitalize whole local
            return letters[:1].upper() + letters[1:]
    return None


def _extract_skills(text: str) -> List[str]:
    skills: List[str] = []
    block = re.search(
        r"(?is)required skills?:?\s*(.+?)(?:preferred skills?|interested candidates|immediate interviews|#|$)",
        text,
    )
    chunk = block.group(1) if block else text
    for line in chunk.splitlines():
        line = line.strip(" •*-–—✅🔹\t")
        if not line or len(line) > 80:
            continue
        if any(
            k in line.lower()
            for k in (
                "flutter",
                "react native",
                "android",
                "ios",
                "swift",
                "kotlin",
                "java",
                "rest",
                "api",
                "git",
                "firebase",
                "ci/cd",
            )
        ):
            skills.append(line.split("(")[0].strip())
    # dedupe keep order
    seen = set()
    out = []
    for s in skills:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            out.append(s)
    return out[:12]


def _guess_location(text: str) -> Optional[str]:
    m = re.search(r"(?i)location\s*[:|]?\s*([^\n]{2,60})", text)
    if m:
        return m.group(1).strip(" 📍")
    if re.search(r"\bUSA\b|\bUnited States\b", text):
        return "USA"
    return None


def parse_hiring_post(
    post_text: str,
    *,
    source_url: Optional[str] = None,
) -> ParsedHiringPost:
    raw = (post_text or "").strip()
    if len(raw) < 40:
        raise ValueError("Paste the full hiring post (or JD) — text is too short.")

    emails = _EMAIL_RE.findall(raw)
    # Prefer non-noreply emails
    contact_email = None
    for e in emails:
        low = e.lower()
        if any(x in low for x in ("noreply", "no-reply", "donotreply")):
            continue
        contact_email = e
        break
    if not contact_email and emails:
        contact_email = emails[0]

    post_urls = _LINKEDIN_POST_RE.findall(raw)
    profile_urls = _LINKEDIN_PROFILE_RE.findall(raw)
    linkedin_post = _clean_linkedin_url(source_url) if source_url else None
    if not linkedin_post and post_urls:
        linkedin_post = _clean_linkedin_url(post_urls[0])
    linkedin_profile = _clean_linkedin_url(profile_urls[0]) if profile_urls else None

    # If source_url is a post URL with username, derive profile
    if linkedin_post and not linkedin_profile:
        m = re.search(r"linkedin\.com/posts/([^_/]+)", linkedin_post, re.I)
        if m:
            linkedin_profile = f"https://www.linkedin.com/in/{m.group(1)}"

    role = _guess_role(raw)
    contact_name = _guess_contact_name(raw, contact_email)
    skills = _extract_skills(raw)
    location = _guess_location(raw)

    warnings: List[str] = []
    if not contact_email:
        warnings.append(
            "No email found in the post — paste one manually before send."
        )
    if not linkedin_post and source_url:
        warnings.append("Source URL did not look like a LinkedIn post link.")

    # Company rarely present on personal LinkedIn hiring posts
    company = "LinkedIn hiring post"
    m_co = re.search(r"(?i)(?:at|@|company)\s+([A-Z][A-Za-z0-9&.,\s]{2,40})", raw)
    if m_co and "resume" not in m_co.group(1).lower():
        company = m_co.group(1).strip()

    description = raw
    if linkedin_post and linkedin_post not in description:
        description = f"{description}\n\nSource: {linkedin_post}"

    return ParsedHiringPost(
        role_title=role,
        company_name=company,
        description=description,
        contact_email=contact_email,
        contact_name=contact_name,
        linkedin_post_url=linkedin_post,
        linkedin_profile_url=linkedin_profile,
        required_skills=skills,
        location=location,
        warnings=warnings,
    )


def build_interest_email(
    *,
    contact_name: Optional[str],
    role_title: str,
    company_name: str,
    candidate_name: str,
    highlight_skills: Optional[List[str]] = None,
    source_url: Optional[str] = None,
) -> tuple[str, str]:
    first = (contact_name or "there").split()[0]
    skills = ", ".join((highlight_skills or [])[:4]) or "mobile app development"
    subject = f"Application — {role_title}"
    if company_name and company_name != "LinkedIn hiring post":
        subject = f"{role_title} at {company_name} — {candidate_name}"

    lines = [
        f"Hi {first},",
        "",
        f"I saw your post about the {role_title} role"
        + (" and I'm very interested." if True else ""),
        "",
        f"I've attached my tailored resume highlighting {skills}. "
        "Happy to share a portfolio or jump on a quick call.",
        "",
    ]
    if source_url:
        lines.append(f"(Re: {source_url})")
        lines.append("")
    lines.extend(
        [
            "Best regards,",
            candidate_name,
        ]
    )
    return subject, "\n".join(lines)
