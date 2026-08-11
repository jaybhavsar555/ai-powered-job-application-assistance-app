from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Tuple
import logging
import re

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.infrastructure.llm.client import structured_generate

logger = logging.getLogger(__name__)

# Common tech / role skills for fast offline matching when LLM is down
_KNOWN_SKILLS = [
    "Flutter", "Dart", "Swift", "Kotlin", "Java", "Python", "JavaScript", "TypeScript",
    "React", "React Native", "Next.js", "Node.js", "Express", "NestJS", "Angular", "Vue",
    "Android", "iOS", "Firebase", "GraphQL", "REST", "gRPC", "SQL", "PostgreSQL", "MySQL",
    "MongoDB", "Redis", "Docker", "Kubernetes", "AWS", "GCP", "Azure", "CI/CD", "Git",
    "Bloc", "Riverpod", "Provider", "GetX", "Redux", "MobX", "SwiftUI", "Jetpack Compose",
    "Hive", "Isar", "SQLite", "Realm", "WebSockets", "Socket.io", "OAuth", "JWT",
    "Agile", "Scrum", "TDD", "Unit Testing", "Integration Testing", "Playwright", "Cypress",
    "Figma", "UI/UX", "Material Design", "Tailwind", "HTML", "CSS", "Sass",
    "Django", "FastAPI", "Flask", "Spring", "Go", "Rust", "C++", "C#", ".NET",
    "Machine Learning", "TensorFlow", "PyTorch", "LLM", "LangChain", "OpenAI",
    "Microservices", "System Design", "OOPs", "Design Patterns", "State Machine",
    "Offline-first", "Push Notifications", "Deep Linking", "App Store", "Play Store",
    "Jira", "Confluence", "Linux", "Bash", "Terraform", "Jenkins", "GitHub Actions",
]


class SkillImpact(BaseModel):
    skill: str = Field(..., description="The skill name exactly as mentioned in the JD")
    level: Literal["high", "medium", "low"] = Field(
        ..., description="Impact level if this skill is added"
    )
    reason: str = Field(
        ..., description="One sentence: why this skill matters for this specific role"
    )
    jd_mentions: int = Field(
        default=1, description="How many times this skill appears/is implied in the JD"
    )


class SkillPresent(BaseModel):
    skill: str = Field(..., description="Skill from JD that IS present in the resume")
    confidence: Literal["strong", "partial"] = Field(
        ..., description="strong = exact match; partial = implied or adjacent"
    )
    note: str = Field(
        default="", description="Brief note on how it's demonstrated in the resume"
    )


class NiceToHaveSkill(BaseModel):
    skill: str = Field(..., description="Nice-to-have skill from the JD")
    reason: str = Field(..., description="Why it's nice-to-have, not required")


class SkillGapAnalysis(BaseModel):
    match_score: int = Field(
        ..., description="Score 0-100: how well the resume matches this specific JD"
    )
    rationale: str = Field(
        ..., description="2-3 sentence summary of the overall match quality"
    )
    missing_skills: List[str] = Field(
        ...,
        description=(
            "Skills explicitly REQUIRED by the JD that are completely absent "
            "from the resume. Be strict — only list skills actually in the JD."
        ),
    )
    skill_impacts: List[SkillImpact] = Field(
        default_factory=list,
        description="Per-skill impact analysis for each missing required skill",
    )
    present_skills: List[SkillPresent] = Field(
        default_factory=list,
        description="Skills from the JD that ARE present in the resume",
    )
    nice_to_have_missing: List[NiceToHaveSkill] = Field(
        default_factory=list,
        description="Nice-to-have / preferred skills from the JD that are absent",
    )
    qualifications_match: str = Field(
        default="",
        description="Brief comment on degree / years of experience fit",
    )


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _count_mentions(haystack: str, skill: str) -> int:
    pattern = re.compile(rf"(?<!\w){re.escape(skill.lower())}(?!\w)", re.I)
    return len(pattern.findall(haystack))


def _split_required_vs_nice(jd: str) -> Tuple[str, str]:
    """Rough split: text after nice-to-have / preferred / bonus is optional."""
    low = jd.lower()
    markers = [
        "nice to have",
        "nice-to-have",
        "preferred qualifications",
        "preferred skills",
        "bonus",
        "good to have",
        "plus points",
    ]
    cut = len(jd)
    for m in markers:
        idx = low.find(m)
        if idx != -1 and idx < cut:
            cut = idx
    if cut >= len(jd):
        return jd, ""
    return jd[:cut], jd[cut:]


def heuristic_skill_gap(resume: str, job_description: str) -> SkillGapAnalysis:
    """
    Fast offline JD↔resume match when Token Harbor / Ollama is unavailable.
    Uses known tech keywords + mention counts — not fake invented skills.
    """
    required_part, nice_part = _split_required_vs_nice(job_description or "")
    resume_l = _norm(resume)
    required_l = _norm(required_part)
    nice_l = _norm(nice_part)
    full_jd_l = _norm(job_description)

    present: List[SkillPresent] = []
    missing: List[str] = []
    impacts: List[SkillImpact] = []
    nice_missing: List[NiceToHaveSkill] = []

    for skill in _KNOWN_SKILLS:
        in_required = _count_mentions(required_l, skill)
        in_nice = _count_mentions(nice_l, skill) if nice_l else 0
        in_jd = in_required or (_count_mentions(full_jd_l, skill) if not nice_l else 0)
        if not in_required and not in_nice and not in_jd:
            continue
        in_resume = _count_mentions(resume_l, skill) > 0

        if in_required or (in_jd and not in_nice):
            if in_resume:
                present.append(
                    SkillPresent(
                        skill=skill,
                        confidence="strong",
                        note="Matched keyword on resume",
                    )
                )
            else:
                missing.append(skill)
                mentions = max(in_required, in_jd, 1)
                level: Literal["high", "medium", "low"] = (
                    "high" if mentions >= 2 else "medium"
                )
                impacts.append(
                    SkillImpact(
                        skill=skill,
                        level=level,
                        reason="Listed in the JD requirements but not found on the resume.",
                        jd_mentions=mentions,
                    )
                )
        elif in_nice and not in_resume:
            nice_missing.append(
                NiceToHaveSkill(
                    skill=skill,
                    reason="Appears in nice-to-have / preferred section of the JD.",
                )
            )

    # Cap lists so UI stays usable
    missing = missing[:12]
    impacts = impacts[:12]
    present = present[:16]
    nice_missing = nice_missing[:8]

    req_total = len(present) + len(missing)
    if req_total == 0:
        score = 55
        rationale = (
            "Heuristic match (AI busy): no strong tech keywords detected in the JD. "
            "Paste a fuller JD or retry when Token Harbor / Ollama is free for a deeper score."
        )
    else:
        score = int(round(100 * len(present) / req_total))
        score = max(25, min(95, score))
        rationale = (
            f"Heuristic match (AI unavailable): {len(present)}/{req_total} required "
            f"keywords found on the resume; {len(missing)} gaps. "
            "Retry Analyze later for a full LLM review, or continue and tailor the gaps below."
        )

    years_jd = re.search(r"(\d+)\+?\s*\+?\s*years?", full_jd_l)
    years_resume = re.search(r"(\d+)\+?\s*\+?\s*years?", resume_l)
    if years_jd and years_resume:
        qual = (
            f"JD asks ~{years_jd.group(1)} years; resume mentions ~{years_resume.group(1)} years "
            "(heuristic — verify manually)."
        )
    elif years_jd:
        qual = f"JD asks ~{years_jd.group(1)} years of experience — confirm against your resume."
    else:
        qual = "Qualifications not clearly stated — review JD years/degree manually."

    return SkillGapAnalysis(
        match_score=score,
        rationale=rationale,
        missing_skills=missing,
        skill_impacts=impacts,
        present_skills=present,
        nice_to_have_missing=nice_missing,
        qualifications_match=qual,
    )


class SkillGapAgent(OSAgent):
    name = "skill_gap_agent"
    description = (
        "Thorough word-by-word analysis of a resume against a job description. "
        "Falls back to keyword heuristic when LLM is busy."
    )
    capabilities = ["analyze"]

    def _mock(self) -> SkillGapAnalysis:
        return SkillGapAnalysis(
            missing_skills=["State-Machine Design", "Advanced OOPs Concepts"],
            match_score=65,
            rationale=(
                "Strong Flutter/Dart foundation but missing explicit state-machine "
                "design patterns and advanced OOPs depth called out in the JD."
            ),
            skill_impacts=[
                SkillImpact(
                    skill="State-Machine Design",
                    level="high",
                    reason="Primary skillset requirement — directly listed in the JD.",
                    jd_mentions=2,
                ),
                SkillImpact(
                    skill="Advanced OOPs Concepts",
                    level="high",
                    reason="Core requirement for the server-driven agentic architecture.",
                    jd_mentions=2,
                ),
            ],
            present_skills=[
                SkillPresent(
                    skill="Flutter",
                    confidence="strong",
                    note="Explicitly listed with production experience",
                ),
                SkillPresent(
                    skill="Dart",
                    confidence="strong",
                    note="Primary language for Flutter development",
                ),
            ],
            nice_to_have_missing=[
                NiceToHaveSkill(
                    skill="Fintech experience",
                    reason="JD says nice to have: fintech — not a hard requirement",
                ),
            ],
            qualifications_match=(
                "Candidate meets the bachelor's degree requirement and experience level."
            ),
        )

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        base_resume = state.get("resume_json", "{}")
        job_details = state.get("job_description", "")

        system_prompt = """You are a rigorous, unbiased ATS specialist and technical recruiter.

Your task is to do a THOROUGH, word-by-word analysis comparing a candidate's resume to a job description.

CRITICAL RULES:
1. Only list skills in 'missing_skills' if they are EXPLICITLY required by the JD AND absent from the resume. Do NOT hallucinate or infer skills not mentioned.
2. Separate what is "required" from what is "nice to have / preferred / bonus" — treat them in different fields.
3. For 'present_skills', identify every JD requirement that IS covered by the resume (builds confidence).
4. For match_score: 100 = perfect match, 0 = totally unrelated. Be accurate, not generous.
5. In rationale, summarize the REAL gaps and strengths honestly in 2-3 sentences.
6. If the JD says "Nice to have: X" or "Preferred: X" or "Bonus: X", put X in nice_to_have_missing, NOT in missing_skills.
7. Count jd_mentions carefully — how many times a skill appears reinforces its importance.
8. Be strict about what's actually in the resume text vs. what you're assuming.
9. Keep arrays compact (max ~10 missing skills) so the response stays short."""

        try:
            import asyncio

            async def _llm_call():
                return await structured_generate(
                    SkillGapAnalysis,
                    [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": (
                                f"=== RESUME ===\n{(base_resume or '')[:3500]}\n\n"
                                f"=== JOB DESCRIPTION ===\n{(job_details or '')[:4000]}\n\n"
                                "Perform a thorough match analysis. Be strict — only skills "
                                "actually in the JD. Keep JSON compact."
                            ),
                        },
                    ],
                    fallback=None,
                    max_tokens=700,
                    timeout=35.0,
                )

            # Hard cap so Tailor never hangs for minutes on Token Harbor
            result = await asyncio.wait_for(_llm_call(), timeout=95.0)
            return {"skill_gap": result.model_dump(), "analysis_mode": "llm"}
        except Exception as exc:
            logger.warning(
                "Skill gap LLM failed (%s) — using keyword heuristic fallback",
                exc,
            )
            heuristic = heuristic_skill_gap(
                str(base_resume or ""), str(job_details or "")
            )
            return {
                "skill_gap": heuristic.model_dump(),
                "analysis_mode": "heuristic",
                "llm_error": str(exc)[:400],
            }


agent_registry.register(SkillGapAgent())
