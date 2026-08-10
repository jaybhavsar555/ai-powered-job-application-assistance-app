"""Draft recruiter cold emails that sound human (JD + resume grounded)."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.core.prompts.registry import prompt_registry
from app.infrastructure.llm.client import structured_generate


class OutreachDraftResult(BaseModel):
    subject_line: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body content")


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _first_name(full: Optional[str]) -> str:
    if not full or not str(full).strip():
        return ""
    return str(full).strip().split()[0]


def _clean_company(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip()).rstrip(".")


def _resume_highlights(resume: dict, limit: int = 2) -> List[str]:
    out: List[str] = []
    for key in (
        "highlights",
        "key_achievements",
        "summary_bullets",
        "tailored_bullets",
        "added_keywords",
    ):
        raw = resume.get(key) or []
        if isinstance(raw, list):
            for item in raw:
                text = _clean_highlight(str(item))
                if text and text not in out:
                    out.append(text)
                if len(out) >= limit:
                    return out
    summary = _clean_highlight(
        str(resume.get("summary") or resume.get("professional_summary") or "")
    )
    if summary:
        first = re.split(r"(?<=[.!?])\s+", summary)[0].strip()
        cleaned = _clean_highlight(first)
        if cleaned:
            out.append(cleaned)
    return out[:limit]


def _jd_focus(job: dict, role: str) -> str:
    skills = job.get("required_skills") or job.get("skills") or []
    if isinstance(skills, list):
        useful = [
            str(s).strip()
            for s in skills
            if str(s).strip() and len(str(s).strip()) > 2 and not str(s).strip().startswith("[")
        ][:3]
        # Prefer role-relevant tokens when role names a stack
        role_l = role.lower()
        preferred = [s for s in useful if s.lower() in role_l or role_l.split()[0] in s.lower()]
        pick = preferred or useful
        if pick:
            if len(pick) == 1:
                return f"what you need for {role} ({pick[0]})"
            return f"what you need for {role} ({', '.join(pick[:3])})"

    raw = str(job.get("description_raw") or job.get("description") or "").strip()
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = re.sub(r"\s+", " ", raw)
    # Drop noisy metadata-looking chunks
    raw = re.sub(r"Location:.*?Salary:.*?(?=[A-Z]|\Z)", " ", raw, flags=re.I)
    raw = re.sub(r"\[.*?\]", " ", raw)
    if len(raw) > 60:
        # First clause only
        clause = re.split(r"[.!?]", raw)[0].strip()
        if 20 < len(clause) < 160:
            return clause[0].lower() + clause[1:] if clause[0].isupper() else clause
    return f"the {role} role"


def _clean_highlight(text: str) -> Optional[str]:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if not t or len(t) < 16:
        return None
    if t.startswith("[") or "Location:" in t or "Salary:" in t:
        return None
    return t[:220]


def _candidate_name(state: dict, resume: dict) -> str:
    for key in ("candidate_name", "full_name", "name"):
        val = state.get(key) or resume.get(key)
        if val and str(val).strip() and str(val).lower() != "candidate":
            return str(val).strip()
    contact = resume.get("contact") if isinstance(resume.get("contact"), dict) else {}
    if contact.get("name") and str(contact["name"]).lower() != "candidate":
        return str(contact["name"]).strip()
    return "Jay Padmakar Bhavsar"


def _role_title(state: dict, job: dict) -> str:
    title = str(
        job.get("role_title") or job.get("title") or state.get("title") or ""
    ).strip()
    low = title.lower()
    fluff = ("great to see", "work together", "join us", "apply now", "thank you")
    if title and len(title) <= 80 and not any(x in low for x in fluff):
        return title
    for key in ("normalized_title", "position", "job_title"):
        alt = str(job.get(key) or "").strip()
        alt_l = alt.lower()
        if alt and len(alt) <= 80 and not any(x in alt_l for x in fluff):
            return alt
    # Last resort: never paste marketing fluff into the email
    if any(x in low for x in fluff) or len(title) > 80:
        return "this role"
    return title or "this role"


def _company_name(state: dict, job: dict, research: dict) -> str:
    return _clean_company(
        str(
            research.get("company_name")
            or state.get("company")
            or job.get("company_name")
            or "the team"
        )
    )


def _real_company_hook(research: dict) -> Optional[str]:
    sources = research.get("sources") or []
    is_mock = any("mock" in str(s).lower() for s in sources) or (
        research.get("_gather") or {}
    ).get("source") == "mock"
    if is_mock:
        return None
    for key in ("recent_news_hooks", "culture_signals"):
        raw = research.get(key) or []
        if isinstance(raw, list) and raw:
            text = str(raw[0]).strip().rstrip(".")
            if text and len(text) > 20:
                return text
    summary = str(research.get("summary") or "").strip()
    if summary and len(summary) > 40:
        return summary.split(".")[0].strip()
    return None


def build_outreach_from_context(state: Dict[str, Any]) -> OutreachDraftResult:
    """Human-sounding fallback when LLM is mock/unavailable."""
    job = _as_dict(state.get("job_details"))
    resume = _as_dict(state.get("tailored_resume"))
    research = _as_dict(state.get("company_research"))
    recruiter = _as_dict(state.get("recruiter_discovery"))

    company = _company_name(state, job, research)
    role = _role_title(state, job)
    candidate = _candidate_name(state, resume)
    highlights = _resume_highlights(resume)
    jd_focus = _jd_focus(job, role)
    hook = _real_company_hook(research)

    recruiter_name = recruiter.get("name") or recruiter.get("recruiter_name")
    if not recruiter_name:
        recruiters = recruiter.get("recruiters")
        if isinstance(recruiters, list) and recruiters and isinstance(recruiters[0], dict):
            recruiter_name = recruiters[0].get("name")
    greet_name = _first_name(str(recruiter_name)) if recruiter_name else ""
    greet = f"Hi {greet_name}," if greet_name and greet_name.lower() != "hiring" else "Hi there,"

    para_why = (
        f"I saw an opening at {company} and wanted to reach out."
        if role in ("this role", "the open role", "open role")
        else f"I saw the {role} opening at {company} and wanted to reach out."
    )
    if hook:
        para_why += f" What caught my eye was {hook[0].lower() + hook[1:] if hook[0].isupper() else hook}."

    if highlights:
        h0 = highlights[0].rstrip(".")
        h0s = h0[0].lower() + h0[1:] if h0 and h0[0].isupper() else h0
        if len(highlights) > 1:
            h1 = highlights[1].rstrip(".")
            h1s = h1[0].lower() + h1[1:] if h1 and h1[0].isupper() else h1
            para_fit = (
                f"Recently I’ve {h0s}, and I’ve also {h1s}. "
                f"That experience maps cleanly to {jd_focus}."
            )
        else:
            para_fit = (
                f"Recently I’ve {h0s}, which maps cleanly to {jd_focus}."
            )
    else:
        para_fit = (
            f"I’ve been doing hands-on work that maps to {jd_focus}, "
            f"and I tailored my resume to this posting."
        )

    body = (
        f"{greet}\n\n"
        f"{para_why}\n\n"
        f"{para_fit}\n\n"
        f"I’ve attached a resume tailored to this JD — happy to clarify anything.\n\n"
        f"If it’s useful, I’d welcome a short call sometime this week or next.\n\n"
        f"Thanks,\n"
        f"{candidate}"
    )

    if role in ("this role", "the open role", "open role"):
        subject = f"Role at {company} — {candidate}"
    else:
        subject = f"{role} at {company} — {candidate}"
    return OutreachDraftResult(subject_line=subject, body=body)


class OutreachDraftAgent(OSAgent):
    name = "outreach_draft_agent"
    description = "Drafts a human cold email from JD + resume (ChatGPT-style, sendable)."
    capabilities = ["llm"]

    def _mock(self, state: Dict[str, Any]) -> OutreachDraftResult:
        return build_outreach_from_context(state)

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        # Always reload prompt from disk (tone iterates often)
        prompt_registry.invalidate(self.name)

        job = _as_dict(state.get("job_details"))
        resume = _as_dict(state.get("tailored_resume"))
        research = _as_dict(state.get("company_research"))
        recruiter = _as_dict(state.get("recruiter_discovery"))

        company_name = _company_name(state, job, research)
        role = _role_title(state, job)
        candidate = _candidate_name(state, resume)
        matching = state.get("matching_skills") or job.get("matching_skills") or []
        package = state.get("apply_package") or {}

        system_prompt = prompt_registry.get_prompt(self.name)
        user_content = (
            f"Write a sendable cold email as if I pasted my JD + resume into ChatGPT.\n\n"
            f"My name: {candidate}\n"
            f"Exact role title: {role}\n"
            f"Company: {company_name}\n\n"
            f"JOB DESCRIPTION:\n{json.dumps(job)[:6500]}\n\n"
            f"MY TAILORED RESUME / HIGHLIGHTS:\n{json.dumps(resume)[:5500]}\n\n"
            f"Matching skills (optional hints, do NOT dump as bullets):\n{json.dumps(matching)}\n\n"
            f"Company research (ignore if mock/generic):\n{json.dumps(research)[:3500]}\n\n"
            f"Package meta:\n{json.dumps(package)[:800]}\n\n"
            f"Recruiter:\n{json.dumps(recruiter)[:1500]}\n\n"
            "Remember: prose only, human tone, mention attached tailored resume once."
        )

        result = await structured_generate(
            OutreachDraftResult,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            fallback=lambda: self._mock(state),
            max_tokens=1100,
        )

        payload = result.model_dump()
        subj = str(payload.get("subject_line") or "").strip()
        body = str(payload.get("body") or "").strip()

        # Guardrails against old robotic templates / wrong titles
        robotic = (
            "based on the job description, here is how",
            "wading through a generic",
            "ship the next milestones",
            "i've been following",
            "tailored application",
        )
        if any(r in body.lower() for r in robotic) or body.count("\n- ") >= 2:
            payload = self._mock(state).model_dump()
            subj = payload["subject_line"]
            body = payload["body"]

        if role and role != "the open role":
            if "Software Engineer" in subj and "Software Engineer" not in role:
                payload["subject_line"] = f"{role} at {company_name} — {candidate}"
        if "attach" not in body.lower() and "resume" not in body.lower():
            payload["body"] = (
                body.rstrip()
                + "\n\nI’ve attached a resume tailored to this job description."
            )

        return {"outreach_draft": payload}


agent_registry.register(OutreachDraftAgent())
