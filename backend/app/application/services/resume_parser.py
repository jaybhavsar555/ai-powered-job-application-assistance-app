"""Resume text parser + Jobscan-style ATS checks (sections, keywords, formatting)."""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, Field

from app.application.agents.skill_gap_agent import _KNOWN_SKILLS, _count_mentions, _norm
from app.schemas.ats import ParserATSReport


_SECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "summary": re.compile(
        r"(?:^|\n)\s*(?:professional\s+)?(?:summary|profile|objective|about)\s*:?\s*\n",
        re.I | re.M,
    ),
    "experience": re.compile(
        r"(?:^|\n)\s*(?:work\s+)?(?:experience|employment|professional\s+experience|projects)\s*:?\s*\n",
        re.I | re.M,
    ),
    "skills": re.compile(
        r"(?:^|\n)\s*(?:technical\s+)?(?:skills|core\s+competencies|technologies|expertise)\s*:?\s*\n",
        re.I | re.M,
    ),
    "education": re.compile(
        r"(?:^|\n)\s*(?:education|academic|qualifications)\s*:?\s*\n",
        re.I | re.M,
    ),
}


class ParsedResume(BaseModel):
    raw_text: str = ""
    sections: dict[str, str] = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None


def _split_sections(text: str) -> dict[str, str]:
    """Split resume text into named sections using common ATS-friendly headers."""
    if not (text or "").strip():
        return {}

    markers: list[tuple[int, str]] = []
    for name, pattern in _SECTION_PATTERNS.items():
        for match in pattern.finditer(text):
            markers.append((match.start(), name))

    if not markers:
        return {"body": text.strip()}

    markers.sort(key=lambda x: x[0])
    sections: dict[str, str] = {}
    for idx, (start, name) in enumerate(markers):
        header_end = text.find("\n", start)
        content_start = header_end + 1 if header_end != -1 else start
        content_end = markers[idx + 1][0] if idx + 1 < len(markers) else len(text)
        chunk = text[content_start:content_end].strip()
        if chunk:
            sections[name] = chunk
    return sections


def _extract_bullets(text: str) -> list[str]:
    bullets: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if re.match(r"^[\u2022\-\*•]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
            cleaned = re.sub(r"^[\u2022\-\*•]\s+|\d+\.\s+", "", stripped).strip()
            if len(cleaned) > 12:
                bullets.append(cleaned)
    return bullets[:40]


def _extract_skills(text: str, sections: dict[str, str]) -> list[str]:
    found: list[str] = []
    haystack = _norm(text)
    skills_block = sections.get("skills") or sections.get("body") or text
    skills_l = _norm(skills_block)
    for skill in _KNOWN_SKILLS:
        if _count_mentions(haystack, skill) > 0:
            found.append(skill)
        elif _count_mentions(skills_l, skill) > 0 and skill not in found:
            found.append(skill)
    return found[:30]


def parse_resume_text(text: str) -> ParsedResume:
    """Parse plain resume text into sections, bullets, and skill tokens."""
    raw = (text or "").strip()
    sections = _split_sections(raw)
    bullets = _extract_bullets(raw)
    skills = _extract_skills(raw, sections)

    email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", raw)
    name = None
    first_lines = [ln.strip() for ln in raw.splitlines() if ln.strip()][:3]
    for ln in first_lines:
        if email_match and email_match.group(0) in ln:
            continue
        if len(ln) < 60 and not re.search(r"\d{3}", ln):
            name = ln
            break

    return ParsedResume(
        raw_text=raw,
        sections=sections,
        skills=skills,
        bullets=bullets,
        contact_name=name,
        contact_email=email_match.group(0) if email_match else None,
    )


def structured_resume_to_text(content: dict) -> str:
    """Render OptimizedResume JSON to plain text for scoring."""
    if not content:
        return ""
    parts: list[str] = []
    summary = content.get("summary") or content.get("professional_summary")
    if summary:
        parts.append(f"Professional Summary\n{summary}")
    bullets = content.get("tailored_bullets") or content.get("bullets") or []
    if bullets:
        parts.append("Experience")
        parts.extend(f"• {b}" for b in bullets if b)
    keywords = content.get("added_keywords") or content.get("skills") or []
    if keywords:
        parts.append("Skills\n" + ", ".join(str(k) for k in keywords))
    experience = content.get("experience") or []
    for block in experience:
        if isinstance(block, dict):
            header = " — ".join(
                x for x in [block.get("title"), block.get("company")] if x
            )
            if header:
                parts.append(header)
            for b in block.get("bullets") or []:
                parts.append(f"• {b}")
    if content.get("manual_override"):
        parts.append(str(content["manual_override"]))
    return "\n\n".join(parts)


def _jd_keywords(job_description: str) -> list[str]:
    jd_l = _norm(job_description)
    keywords: list[str] = []
    for skill in _KNOWN_SKILLS:
        if _count_mentions(jd_l, skill) > 0:
            keywords.append(skill)
    # Short capitalized tokens (2–4 words) often used as requirements
    for token in re.findall(r"\b[A-Z][a-zA-Z+.#/]{1,24}(?:\s+[A-Z][a-zA-Z+.#/]{1,24}){0,2}\b", job_description or ""):
        if len(token) > 2 and token not in keywords:
            keywords.append(token)
    return keywords[:40]


def run_parser_checks(parsed: ParsedResume, job_description: str) -> ParserATSReport:
    """Compute section, keyword-density, and formatting checks vs a JD."""
    warnings: list[str] = []
    suggestions: list[str] = []
    formatting_flags: list[str] = []

    sections = parsed.sections
    has_summary = "summary" in sections or bool(re.search(r"summary|profile|objective", parsed.raw_text[:800], re.I))
    has_experience = "experience" in sections or len(parsed.bullets) >= 2
    has_skills = "skills" in sections or len(parsed.skills) >= 3
    has_education = "education" in sections or bool(re.search(r"\b(b\.?s\.?|bachelor|master|ph\.?d|university|college)\b", parsed.raw_text, re.I))

    if not has_summary:
        warnings.append("No clear Professional Summary section detected.")
        suggestions.append("Add a 2–3 line summary with top JD keywords near the top.")
    if not has_experience:
        warnings.append("Experience section or bullet points not detected.")
        suggestions.append("Use bullet points under Experience with measurable outcomes.")
    if not has_skills:
        warnings.append("Skills section not clearly labeled.")
        suggestions.append("Add a Skills section listing JD keywords (comma-separated).")
    if not has_education and re.search(r"degree|bachelor|master|ph\.?d", _norm(job_description)):
        warnings.append("Education section not detected but JD mentions degree requirements.")

    raw_len = len(parsed.raw_text)
    if raw_len < 400:
        formatting_flags.append("very_short")
        warnings.append("Resume text is very short — ATS may rank it lower.")
    if raw_len > 12000:
        formatting_flags.append("very_long")
        warnings.append("Resume is very long — consider trimming to 1–2 pages.")

    if len(parsed.bullets) == 0:
        formatting_flags.append("no_bullet_points")
        suggestions.append("Convert dense paragraphs into bullet points for ATS parsing.")

    jd_keys = _jd_keywords(job_description)
    resume_l = _norm(parsed.raw_text)
    summary_l = _norm(sections.get("summary", ""))
    skills_l = _norm(sections.get("skills", ""))
    experience_l = _norm(sections.get("experience", ""))

    matched = [k for k in jd_keys if _count_mentions(resume_l, k) > 0]
    density = (len(matched) / len(jd_keys)) if jd_keys else 0.0

    kw_summary = sum(1 for k in matched if _count_mentions(summary_l, k) > 0)
    kw_skills = sum(1 for k in matched if _count_mentions(skills_l, k) > 0)
    kw_exp = sum(1 for k in matched if _count_mentions(experience_l, k) > 0)

    section_bits = [has_summary, has_experience, has_skills, has_education]
    section_score = int(round(100 * sum(section_bits) / len(section_bits)))

    if jd_keys:
        placement_score = int(
            round(
                100
                * (
                    0.5 * (kw_summary / max(len(matched), 1))
                    + 0.3 * (kw_skills / max(len(matched), 1))
                    + 0.2 * (kw_exp / max(len(matched), 1))
                )
            )
        )
    else:
        placement_score = 60

    density_score = int(round(min(1.0, density) * 100))
    overall = int(round(0.4 * section_score + 0.35 * density_score + 0.25 * placement_score))
    overall = max(0, min(100, overall))

    if density < 0.35 and jd_keys:
        suggestions.append(
            f"Only {len(matched)}/{len(jd_keys)} JD keywords found — weave missing terms into summary and bullets."
        )

    return ParserATSReport(
        has_summary_section=has_summary,
        has_experience_section=has_experience,
        has_skills_section=has_skills,
        has_education_section=has_education,
        keyword_density=round(density, 3),
        keywords_in_summary=kw_summary,
        keywords_in_skills=kw_skills,
        keywords_in_experience=kw_exp,
        formatting_flags=formatting_flags,
        section_score=section_score,
        placement_score=placement_score,
        overall_parser_score=overall,
        warnings=warnings[:6],
        suggestions=suggestions[:6],
    )
