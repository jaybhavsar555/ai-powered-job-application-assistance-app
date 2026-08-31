"""Static portfolio export from confirmed Loop Engineer packets / resume."""

from __future__ import annotations

import html
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.config import get_settings
from app.infrastructure.resume_library import extract_text, list_resume_files

logger = logging.getLogger(__name__)


def _portfolio_root() -> Path:
    settings = get_settings()
    root = Path(getattr(settings, "PORTFOLIO_EXPORT_DIR", None) or "./data/portfolio")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _user_portfolio_dir(user_id: UUID) -> Path:
    d = _portfolio_root() / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


class PortfolioExportService:
    def export_from_packet(
        self,
        user_id: UUID,
        packet: Dict[str, Any],
        *,
        user_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Write index.html + profile.json from a confirmed job packet's tailored resume."""
        job = packet.get("job") or {}
        tailored = packet.get("tailored_resume") or {}
        research = packet.get("company_research") or {}

        name = self._display_name(user_email)
        summary = (tailored.get("summary") or "").strip()
        bullets: List[str] = list(tailored.get("tailored_bullets") or [])[:8]
        keywords: List[str] = list(tailored.get("added_keywords") or [])[:20]

        if not summary and not bullets:
            summary, bullets, keywords = self._fallback_from_resume_library()

        latest_role = (job.get("title") or "Software Engineer").strip()
        target_line = f"Targeting: {latest_role}"
        if job.get("company"):
            target_line += f" @ {job.get('company')}"

        profile = {
            "name": name,
            "summary": summary,
            "highlights": bullets,
            "skills": keywords,
            "latest_target": target_line,
            "company_research_blurb": (research.get("summary") or "")[:500],
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "source": "loop_engineer_packet",
            "packet_id": packet.get("id"),
        }

        out_dir = _user_portfolio_dir(user_id)
        (out_dir / "profile.json").write_text(
            json.dumps(profile, indent=2), encoding="utf-8"
        )

        html_content = self._render_html(profile)
        html_path = out_dir / "index.html"
        html_path.write_text(html_content, encoding="utf-8")

        return {
            "ok": True,
            "html_path": str(html_path),
            "json_path": str(out_dir / "profile.json"),
            "preview_url": f"/api/v1/loop-engineer/portfolio/preview",
            "note": "Static export only — review before publishing anywhere public.",
        }

    def get_export_paths(self, user_id: UUID) -> Dict[str, Any]:
        out_dir = _user_portfolio_dir(user_id)
        html_path = out_dir / "index.html"
        json_path = out_dir / "profile.json"
        return {
            "exists": html_path.exists(),
            "html_path": str(html_path) if html_path.exists() else None,
            "json_path": str(json_path) if json_path.exists() else None,
        }

    def read_html(self, user_id: UUID) -> Optional[str]:
        path = _user_portfolio_dir(user_id) / "index.html"
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _display_name(email: Optional[str]) -> str:
        if not email or "@" not in email:
            return "Candidate"
        local = email.split("@")[0]
        bits = [b for b in local.replace(".", " ").replace("_", " ").split() if b]
        return " ".join(b.capitalize() for b in bits[:3]) or "Candidate"

    def _fallback_from_resume_library(self) -> tuple[str, List[str], List[str]]:
        source = Path(get_settings().RESUME_SOURCE_DIR)
        files = list_resume_files(source) if source.exists() else []
        if not files:
            return ("Professional software engineer.", [], [])
        text = extract_text(files[0].path)[:3000]
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        summary = lines[0][:400] if lines else text[:400]
        bullets = [ln for ln in lines[1:6] if len(ln) > 20][:5]
        return summary, bullets, []

    @staticmethod
    def _render_html(profile: Dict[str, Any]) -> str:
        name = html.escape(str(profile.get("name") or "Candidate"))
        summary = html.escape(str(profile.get("summary") or ""))
        target = html.escape(str(profile.get("latest_target") or ""))
        blurb = html.escape(str(profile.get("company_research_blurb") or ""))
        bullets = profile.get("highlights") or []
        skills = profile.get("skills") or []
        updated = html.escape(str(profile.get("updated_at") or "")[:19])

        bullet_html = "".join(
            f"<li>{html.escape(str(b))}</li>" for b in bullets if b
        )
        skill_html = " ".join(
            f'<span class="tag">{html.escape(str(s))}</span>' for s in skills if s
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{name} — Portfolio</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; line-height: 1.5; color: #111; }}
    h1 {{ margin-bottom: 0.25rem; }}
    .muted {{ color: #666; font-size: 0.9rem; }}
    .tag {{ display: inline-block; background: #eef2ff; color: #3730a3; padding: 0.15rem 0.5rem; border-radius: 4px; margin: 0.15rem; font-size: 0.85rem; }}
    ul {{ padding-left: 1.25rem; }}
    footer {{ margin-top: 2rem; font-size: 0.8rem; color: #888; }}
  </style>
</head>
<body>
  <h1>{name}</h1>
  <p class="muted">{target}</p>
  <p>{summary}</p>
  {"<h2>Highlights</h2><ul>" + bullet_html + "</ul>" if bullet_html else ""}
  {"<h2>Skills</h2><p>" + skill_html + "</p>" if skill_html else ""}
  {"<h2>Recent research</h2><p class='muted'>" + blurb + "</p>" if blurb else ""}
  <footer>Exported by Career OS Loop Engineer · {updated} UTC</footer>
</body>
</html>"""
