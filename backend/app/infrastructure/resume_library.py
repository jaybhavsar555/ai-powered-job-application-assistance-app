"""Scan local resume folder and pick the best base resume for a JD/role."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from app.core.target_roles import TARGET_ROLES

RESUME_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


@dataclass
class ResumeFile:
    path: Path
    role_hint: str
    label: str

    @property
    def name(self) -> str:
        return self.path.name


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def detect_role_family(role_title: str, job_description: str = "") -> str:
    blob = f"{role_title}\n{job_description}".lower()
    scores: dict[str, int] = {}
    for role in TARGET_ROLES:
        score = 0
        for kw in role["keywords"]:
            if kw.lower() in blob:
                score += 2 if kw.lower() in role_title.lower() else 1
        scores[role["id"]] = score
    best = max(scores, key=scores.get)
    if scores[best] <= 0:
        return "fullstack"
    return best


def classify_filename(name: str) -> str:
    token = _normalize(name)
    for role in TARGET_ROLES:
        for hint in role["preferred_resume_tokens"]:
            if hint.replace("-", "_") in token:
                return role["id"]
    return "general"


def list_resume_files(source_dir: Path) -> List[ResumeFile]:
    if not source_dir.exists() or not source_dir.is_dir():
        return []

    files: List[ResumeFile] = []
    # Prefer top-level templates; skip company subfolders that look like past packages
    for path in sorted(source_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in RESUME_EXTENSIONS:
            continue
        lower = path.name.lower()
        if "cover_letter" in lower or "cover letter" in lower:
            continue
        hint = classify_filename(path.name)
        files.append(
            ResumeFile(
                path=path,
                role_hint=hint,
                label=path.stem.replace("_", " "),
            )
        )
    return files


def pick_base_resume(source_dir: Path, role_family: str) -> Optional[ResumeFile]:
    files = list_resume_files(source_dir)
    if not files:
        return None

    preferred = [f for f in files if f.role_hint == role_family]
    if preferred:
        # Prefer pdf, then names that mention the family, then longer/more specific names
        preferred.sort(
            key=lambda f: (
                0 if f.path.suffix.lower() == ".pdf" else 1,
                0 if role_family.replace("_", "") in _normalize(f.name) else 1,
                -len(f.name),
            )
        )
        return preferred[0]

    general = [f for f in files if f.role_hint in ("general", "fullstack", "sde")]
    pool = general or files
    pool.sort(key=lambda f: (0 if f.path.suffix.lower() == ".pdf" else 1, -len(f.name)))
    return pool[0]


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        parts = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(parts).strip()
    if suffix == ".docx":
        from docx import Document

        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text).strip()
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def parse_contact(resume_text: str) -> tuple[str, str]:
    """Return (full_name, contact_line)."""
    lines = [ln.strip() for ln in resume_text.splitlines() if ln.strip()]
    name = lines[0] if lines else "Candidate"
    # Avoid treating a title line as name
    if len(name) > 60 or "|" in name:
        name = "Jay Padmakar Bhavsar"

    email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", resume_text)
    phone_match = re.search(r"(?:\+?\d[\d\s-]{8,}\d)", resume_text)
    bits: List[str] = []
    if email_match:
        bits.append(email_match.group(0).replace(" ", ""))
    if phone_match:
        bits.append(re.sub(r"\s+", " ", phone_match.group(0)).strip())
    location_match = re.search(r"(Mumbai|Pune|Bengaluru|Bangalore|Remote)[^\n,]{0,40}", resume_text, re.I)
    if location_match:
        bits.append(location_match.group(0).strip())
    return name, " | ".join(bits) if bits else ""


def slugify(value: str, fallback: str = "package") -> str:
    cleaned = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip()
    cleaned = re.sub(r"[-\s]+", "_", cleaned)
    return cleaned[:80] or fallback


def missing_skills_from_job(required: Iterable[str], resume_text: str) -> List[str]:
    lower = resume_text.lower()
    missing = []
    for skill in required:
        s = (skill or "").strip()
        if not s:
            continue
        if s.lower() not in lower:
            missing.append(s)
    return missing[:12]
