"""Obsidian vault sync — unit tests (filesystem only, no Postgres required for scaffold)."""

from pathlib import Path
from uuid import uuid4

import pytest

from app.application.services.obsidian_vault import (
    ObsidianVaultService,
    _slug,
    _frontmatter,
)


def test_slug_and_frontmatter():
    assert "Acme" in _slug("Acme Labs!")
    fm = _frontmatter({"type": "application", "tags": ["a", "b"], "score": 80})
    assert fm.startswith("---")
    assert "type:" in fm
    assert "- \"a\"" in fm or "- a" in fm.replace('"', "")


@pytest.mark.asyncio
async def test_scaffold_and_daily(tmp_path, monkeypatch):
    from unittest.mock import AsyncMock, MagicMock

    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))
    # Reset settings cache if any
    from app.core import config as cfg

    cfg.get_settings.cache_clear()

    db = MagicMock()
    # sync_all / daily need DB queries — mock empty applications
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result)

    service = ObsidianVaultService(db)
    out = await service.ensure_scaffold()
    assert out["configured"] is True
    career = Path(out["career_os_folder"])
    assert (career / "Dashboard.md").is_file()
    assert (career / "Applications").is_dir()

    daily = await service.write_daily_learning(uuid4(), minutes=30, track_id="python")
    assert daily["status"] == "ok"
    assert Path(daily["file"]).is_file()
    text = Path(daily["file"]).read_text(encoding="utf-8")
    assert "Python" in text or "python" in text.lower()
    assert "Block 2" in text

    cfg.get_settings.cache_clear()
