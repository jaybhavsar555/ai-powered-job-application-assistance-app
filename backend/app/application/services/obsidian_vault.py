"""Obsidian second-brain: write Career OS applications, prep, and daily learning as Markdown."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.infrastructure.db.models import DBApplication, DBInterviewPrep, DBJob
from app.application.services.resume_parser import structured_resume_to_text


# Frameworks / fundamentals the daily coach rotates through
DEFAULT_LEARNING_TRACKS = [
    {"id": "dsa", "title": "Data Structures & Algorithms", "focus": "arrays, hash maps, two pointers, trees, complexity"},
    {"id": "system_design", "title": "System Design Fundamentals", "focus": "load balancing, caching, CAP, queues, databases"},
    {"id": "python", "title": "Python Core", "focus": "async, typing, GIL, packaging, testing"},
    {"id": "fastapi", "title": "FastAPI / Backend", "focus": "routing, DI, pydantic, auth, background tasks"},
    {"id": "react", "title": "React / Frontend", "focus": "hooks, state, rendering, suspense, forms"},
    {"id": "sql", "title": "SQL & Postgres", "focus": "indexes, joins, EXPLAIN, transactions, migrations"},
    {"id": "docker", "title": "Docker & DevOps", "focus": "images, compose, networking, volumes, CI"},
    {"id": "behavioral", "title": "Behavioral / STAR", "focus": "ownership, conflict, failure stories mapped to resume"},
]


def _slug(text: str, fallback: str = "note") -> str:
    cleaned = re.sub(r"[^\w\s\-]+", "", (text or "").strip(), flags=re.UNICODE)
    cleaned = re.sub(r"[\s_]+", "-", cleaned).strip("-")
    return (cleaned[:80] or fallback)


def _yaml_escape(value: Any) -> str:
    if value is None:
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def _frontmatter(fields: dict[str, Any]) -> str:
    lines = ["---"]
    for key, val in fields.items():
        if isinstance(val, list):
            lines.append(f"{key}:")
            for item in val:
                lines.append(f"  - {_yaml_escape(item)}")
        else:
            lines.append(f"{key}: {_yaml_escape(val)}")
    lines.append("---")
    return "\n".join(lines)


class ObsidianVaultService:
    """Sync Career OS data into a local Obsidian vault (e.g. Jay OS)."""

    ROOT_FOLDER = "Career OS"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    def vault_root(self) -> Path:
        raw = (self.settings.OBSIDIAN_VAULT_PATH or "").strip()
        if not raw:
            raise HTTPException(
                status_code=400,
                detail=(
                    "OBSIDIAN_VAULT_PATH is not set. "
                    "Point it at your Obsidian vault (e.g. Jay OS folder) in backend/.env."
                ),
            )
        path = Path(raw).expanduser()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot access Obsidian vault path {path}: {exc}",
            ) from exc
        return path.resolve()

    def career_root(self) -> Path:
        root = self.vault_root() / self.ROOT_FOLDER
        for sub in (
            "Applications",
            "Interview Prep",
            "Daily",
            "Learning/Topics",
            "Learning/Practice",
            "Templates",
            "MOCs",
        ):
            (root / sub).mkdir(parents=True, exist_ok=True)
        return root

    def status(self) -> dict[str, Any]:
        try:
            root = self.vault_root()
            career = root / self.ROOT_FOLDER
            apps = list((career / "Applications").glob("*.md")) if career.exists() else []
            daily = list((career / "Daily").glob("*.md")) if career.exists() else []
            return {
                "configured": True,
                "vault_path": str(root),
                "career_os_folder": str(career),
                "exists": root.exists(),
                "writable": root.exists() and root.is_dir(),
                "application_notes": len(apps),
                "daily_notes": len(daily),
                "hint": (
                    "Open this folder as an Obsidian vault (or nest Career OS inside Jay OS). "
                    "On Windows set OBSIDIAN_VAULT_PATH to C:\\\\Users\\\\Asus\\\\OneDrive\\\\Desktop\\\\Jay OS"
                ),
            }
        except HTTPException as exc:
            return {
                "configured": False,
                "vault_path": self.settings.OBSIDIAN_VAULT_PATH or "",
                "error": exc.detail,
                "hint": (
                    "Set OBSIDIAN_VAULT_PATH in backend/.env to your Jay OS vault path, "
                    "then Sync Applications."
                ),
            }

    async def ensure_scaffold(self) -> dict[str, Any]:
        """Create Career OS folders + dashboard + templates inside the vault."""
        root = self.career_root()
        dashboard = root / "Dashboard.md"
        if not dashboard.exists():
            dashboard.write_text(
                _frontmatter(
                    {
                        "type": "dashboard",
                        "tags": ["career-os", "moc"],
                        "updated": datetime.utcnow().isoformat(),
                    }
                )
                + "\n\n# Career OS Dashboard\n\n"
                + "## Today\n- Open [[Daily/"
                + date.today().isoformat()
                + "]]\n- Review [[MOCs/Applications MOC]]\n- Run Sync from Career OS → Second Brain\n\n"
                + "## Pipelines\n"
                + "- [[MOCs/Applications MOC|Applications]]\n"
                + "- [[MOCs/Interview Prep MOC|Interview Prep]]\n"
                + "- [[MOCs/Learning MOC|Daily Learning]]\n\n"
                + "> Synced from AI Job Application Assistant (Career OS).\n",
                encoding="utf-8",
            )

        moc_apps = root / "MOCs" / "Applications MOC.md"
        if not moc_apps.exists():
            moc_apps.write_text(
                "# Applications MOC\n\nDataview or manual links to notes under `Applications/`.\n",
                encoding="utf-8",
            )
        moc_prep = root / "MOCs" / "Interview Prep MOC.md"
        if not moc_prep.exists():
            moc_prep.write_text(
                "# Interview Prep MOC\n\nNotes under `Interview Prep/` when stage is Shortlisted or Interview.\n",
                encoding="utf-8",
            )
        moc_learn = root / "MOCs" / "Learning MOC.md"
        if not moc_learn.exists():
            moc_learn.write_text(
                "# Learning MOC\n\nDaily notes + topic drills under `Learning/`.\n",
                encoding="utf-8",
            )

        tpl = root / "Templates" / "Application.md"
        if not tpl.exists():
            tpl.write_text(
                "---\ntype: application\ncompany: \"\"\nrole: \"\"\nstage: Wishlist\n"
                "applied_at: \"\"\nats_score:\ntags: [application]\n---\n\n"
                "# {{company}} — {{role}}\n\n## Job Description\n\n## Resume used\n\n## Notes\n\n",
                encoding="utf-8",
            )

        return {"status": "ok", "career_os_folder": str(root), **self.status()}

    async def sync_all(self, user_id: UUID) -> dict[str, Any]:
        await self.ensure_scaffold()
        result = await self.db.execute(
            select(DBApplication)
            .where(DBApplication.user_id == user_id)
            .options(
                selectinload(DBApplication.job).selectinload(DBJob.company),
                selectinload(DBApplication.resume_versions),
                selectinload(DBApplication.interview_prep),
            )
            .order_by(DBApplication.updated_at.desc())
        )
        apps = list(result.scalars().all())
        written: list[str] = []
        for app in apps:
            path = await self.sync_application(user_id, app.id, app=app)
            written.append(path)
        self._write_applications_moc(written)
        return {
            "status": "ok",
            "synced": len(written),
            "files": written,
            **self.status(),
        }

    async def sync_application(
        self,
        user_id: UUID,
        application_id: UUID,
        *,
        app: Optional[DBApplication] = None,
    ) -> str:
        await self.ensure_scaffold()
        if app is None:
            result = await self.db.execute(
                select(DBApplication)
                .where(
                    DBApplication.id == application_id,
                    DBApplication.user_id == user_id,
                )
                .options(
                    selectinload(DBApplication.job).selectinload(DBJob.company),
                    selectinload(DBApplication.resume_versions),
                    selectinload(DBApplication.interview_prep),
                )
            )
            app = result.scalars().first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        job = app.job
        company = "Unknown"
        if job and job.company and job.company.name:
            company = job.company.name
        elif job and isinstance(job.description_normalized, dict):
            company = str(job.description_normalized.get("company_name") or "Unknown")
        role = (job.role_title if job else None) or "Open Role"
        state = app.workflow_state or {}
        tailored = state.get("tailored_resume") or {}
        if not tailored and app.resume_versions:
            latest = sorted(
                app.resume_versions,
                key=lambda v: v.created_at or datetime.min,
                reverse=True,
            )[0]
            tailored = latest.tailored_content or {}

        resume_text = structured_resume_to_text(tailored) if isinstance(tailored, dict) else str(tailored or "")
        jd = (job.description_raw if job else "") or ""
        ats = state.get("ats_score")
        filename = f"{_slug(company)} - {_slug(role)}.md"
        path = self.career_root() / "Applications" / filename

        # Preserve user notes section if they edited the file
        user_notes = ""
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            marker = "## My notes"
            if marker in existing:
                user_notes = existing.split(marker, 1)[1].strip()

        fm = _frontmatter(
            {
                "type": "application",
                "application_id": str(app.id),
                "job_id": str(app.job_id),
                "company": company,
                "role": role,
                "stage": app.stage or "Wishlist",
                "url": (job.url if job else "") or "",
                "ats_score": ats if ats is not None else "",
                "updated": datetime.utcnow().isoformat(),
                "tags": ["career-os", "application", _slug(app.stage or "wishlist").lower()],
            }
        )
        body = [
            fm,
            "",
            f"# {company} — {role}",
            "",
            f"- **Stage:** `{app.stage}`",
            f"- **ATS score:** {ats if ats is not None else '—'}",
            f"- **Job URL:** {(job.url if job else None) or '—'}",
            f"- **Application ID:** `{app.id}`",
            "",
            "## Job description",
            "",
            jd.strip()[:20000] if jd.strip() else "_No JD stored yet._",
            "",
            "## Resume content used",
            "",
            resume_text.strip()[:15000] if resume_text.strip() else "_No tailored resume yet — run Tailor or Canvas._",
            "",
            "## ATS evidence",
            "",
            f"- Matching: {', '.join(state.get('matching_skills') or []) or '—'}",
            f"- Missing: {', '.join(state.get('missing_skills') or []) or '—'}",
            f"- Recommendation: {state.get('ats_recommendation') or '—'}",
            "",
            "## My notes",
            "",
            user_notes or "_Add interview dates, recruiter names, follow-ups…_",
            "",
            "## Links",
            "",
            f"- Dashboard: [[Dashboard]]",
            f"- Interview prep: [[Interview Prep/{_slug(company)} - {_slug(role)}]]",
            "",
        ]
        path.write_text("\n".join(body), encoding="utf-8")

        stage = (app.stage or "").lower()
        if stage in {"shortlisted", "interview"}:
            await self._write_interview_prep_note(app, company, role)

        return str(path)

    async def _write_interview_prep_note(
        self, app: DBApplication, company: str, role: str
    ) -> Path:
        prep: Optional[DBInterviewPrep] = app.interview_prep
        filename = f"{_slug(company)} - {_slug(role)}.md"
        path = self.career_root() / "Interview Prep" / filename
        dossier = ""
        tech: list = []
        behavioral: list = []
        pitches: list = []
        if prep:
            dossier = prep.company_dossier if isinstance(prep.company_dossier, str) else str(prep.company_dossier or "")
            tech = prep.technical_drills or []
            behavioral = prep.behavioral_drills or []
            pitches = prep.pitch_ideas or []

        fm = _frontmatter(
            {
                "type": "interview-prep",
                "application_id": str(app.id),
                "company": company,
                "role": role,
                "stage": app.stage,
                "tags": ["career-os", "interview", "prep"],
                "updated": datetime.utcnow().isoformat(),
            }
        )
        lines = [
            fm,
            "",
            f"# Interview prep — {company} / {role}",
            "",
            f"Linked application: [[Applications/{_slug(company)} - {_slug(role)}]]",
            "",
            "## Company dossier",
            "",
            dossier or "_Generate prep in Career OS (Tracker → Interview → Prep Guide)._",
            "",
            "## Technical drills",
            "",
        ]
        if tech:
            for d in tech:
                if isinstance(d, dict):
                    lines.append(f"### {d.get('topic', 'Topic')}")
                    lines.append(f"**Q:** {d.get('question', '')}")
                    lines.append(f"**Guide:** {d.get('suggested_answer', '')}")
                    lines.append("")
        else:
            lines.append("_No drills yet._\n")

        lines.extend(["## Behavioral drills (STAR)", ""])
        if behavioral:
            for d in behavioral:
                if isinstance(d, dict):
                    lines.append(f"### {d.get('behavioral_theme', 'Theme')}")
                    lines.append(f"**Q:** {d.get('question', '')}")
                    lines.append(f"**Map to:** {d.get('star_mapping', '')}")
                    lines.append("")
        else:
            lines.append("_No behavioral drills yet._\n")

        lines.extend(["## Pitch ideas", ""])
        if pitches:
            for p in pitches:
                if isinstance(p, dict):
                    lines.append(f"- **{p.get('title', '')}:** {p.get('description', '')}")
        else:
            lines.append("_None yet._")

        lines.extend(
            [
                "",
                "## Practice checklist",
                "",
                "- [ ] Re-read JD and call out 5 must-hit keywords",
                "- [ ] Walk through one system-design whiteboard (15 min)",
                "- [ ] Rehearse 2 STAR stories out loud",
                "- [ ] Prepare 3 questions for the interviewer",
                "",
            ]
        )
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def _write_applications_moc(self, files: list[str]) -> None:
        moc = self.career_root() / "MOCs" / "Applications MOC.md"
        links = []
        for f in files:
            name = Path(f).stem
            links.append(f"- [[Applications/{name}]]")
        moc.write_text(
            _frontmatter(
                {
                    "type": "moc",
                    "tags": ["moc", "applications"],
                    "updated": datetime.utcnow().isoformat(),
                }
            )
            + "\n\n# Applications MOC\n\n"
            + "\n".join(links)
            + "\n",
            encoding="utf-8",
        )

    async def write_daily_learning(
        self,
        user_id: UUID,
        *,
        day: Optional[date] = None,
        minutes: int = 45,
        track_id: Optional[str] = None,
        custom_focus: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create/overwrite today's learning note with fundamentals + practice prompts."""
        await self.ensure_scaffold()
        day = day or date.today()
        # Rotate track by day-of-year unless overridden
        track = None
        if track_id:
            track = next((t for t in DEFAULT_LEARNING_TRACKS if t["id"] == track_id), None)
        if not track:
            track = DEFAULT_LEARNING_TRACKS[day.timetuple().tm_yday % len(DEFAULT_LEARNING_TRACKS)]

        # Pull missing skills from recent applications for personalization
        result = await self.db.execute(
            select(DBApplication)
            .where(DBApplication.user_id == user_id)
            .order_by(DBApplication.updated_at.desc())
            .limit(12)
        )
        apps = list(result.scalars().all())
        gap_skills: list[str] = []
        for app in apps:
            state = app.workflow_state or {}
            for s in state.get("missing_skills") or []:
                if s not in gap_skills:
                    gap_skills.append(str(s))
            if len(gap_skills) >= 8:
                break

        focus = custom_focus or track["focus"]
        filename = f"{day.isoformat()}.md"
        path = self.career_root() / "Daily" / filename
        topic_path = self.career_root() / "Learning" / "Topics" / f"{_slug(track['title'])}.md"

        practice_block = [
            f"## Today's focus — {track['title']} ({minutes} min)",
            "",
            f"**Core ideas:** {focus}",
            "",
            "### Block 1 — Concepts (15–20 min)",
            "- Write 5 bullet notes in your own words under [[Learning/Topics/"
            + _slug(track["title"])
            + "]].",
            "- Explain one concept as if teaching a junior engineer.",
            "",
            "### Block 2 — Code practice (20–25 min)",
            "- Solve 1–2 problems (LeetCode/Easy–Medium or a tiny CLI kata) tied to today's focus.",
            "- Commit a short snippet or pseudo-code in `Learning/Practice/`.",
            "",
            "### Block 3 — Job-market glue (5–10 min)",
            "- Map today's topic to 1 bullet you could add to a tailored resume.",
            "- If shortlisted somewhere, rehearse one related interview answer.",
            "",
        ]
        if gap_skills:
            practice_block.extend(
                [
                    "### Skills from your open applications",
                    "",
                    ", ".join(f"`{s}`" for s in gap_skills[:8]),
                    "",
                    "_Prioritize any of these that overlap with today's track._",
                    "",
                ]
            )

        fm = _frontmatter(
            {
                "type": "daily-learning",
                "date": day.isoformat(),
                "track": track["id"],
                "minutes": minutes,
                "tags": ["career-os", "daily", "learning", track["id"]],
            }
        )
        content = (
            fm
            + "\n\n"
            + f"# Daily learning — {day.isoformat()}\n\n"
            + "\n".join(practice_block)
            + "\n## Reflection\n\n- What clicked?\n- What is still fuzzy?\n- Tomorrow's micro-goal:\n"
        )
        path.write_text(content, encoding="utf-8")

        if not topic_path.exists():
            topic_path.write_text(
                _frontmatter(
                    {
                        "type": "learning-topic",
                        "track": track["id"],
                        "tags": ["learning", track["id"]],
                    }
                )
                + f"\n\n# {track['title']}\n\n## Notes\n\n",
                encoding="utf-8",
            )

        return {
            "status": "ok",
            "date": day.isoformat(),
            "track": track,
            "file": str(path),
            "topic_file": str(topic_path),
            "gap_skills": gap_skills[:8],
            **self.status(),
        }
