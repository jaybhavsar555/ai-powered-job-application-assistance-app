"""Loop Engineer v1 — watchlist, schedule, digest unit tests."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.application.services import loop_engineer as le


@pytest.fixture()
def loop_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(le, "_loop_root", lambda: tmp_path)
    return tmp_path


def test_default_schedule(loop_dir):
    svc = le.LoopEngineerService(db=None)  # type: ignore[arg-type]
    sched = svc.default_schedule()
    assert sched["enabled"] is False
    assert sched["interval_hours"] >= 1
    assert "preferences" in sched


def test_save_and_load_schedule(loop_dir):
    user_id = uuid4()
    svc = le.LoopEngineerService(db=None)  # type: ignore[arg-type]
    saved = svc.save_schedule(
        user_id,
        {
            "enabled": True,
            "interval_hours": 12,
            "watchlist_only": True,
            "preferences": {"targetRoles": "backend engineer"},
        },
    )
    assert saved["enabled"] is True
    assert saved["interval_hours"] == 12
    assert saved["watchlist_only"] is True
    assert saved["preferences"]["targetRoles"] == "backend engineer"

    path = loop_dir / str(user_id) / "schedule.json"
    assert path.exists()


def test_is_due_when_never_run(loop_dir):
    svc = le.LoopEngineerService(db=None)  # type: ignore[arg-type]
    sched = svc.default_schedule()
    sched["enabled"] = True
    assert svc._is_due(sched) is True


def test_is_due_when_recently_run(loop_dir):
    svc = le.LoopEngineerService(db=None)  # type: ignore[arg-type]
    sched = svc.default_schedule()
    sched["enabled"] = True
    sched["last_run_at"] = le._utc_now_iso()
    sched["interval_hours"] = 24
    assert svc._is_due(sched) is False


@pytest.mark.asyncio
async def test_list_scheduled_user_ids(loop_dir):
    user_id = uuid4()
    sched_path = loop_dir / str(user_id)
    sched_path.mkdir(parents=True)
    (sched_path / "schedule.json").write_text(
        json.dumps({"enabled": True, "interval_hours": 24}),
        encoding="utf-8",
    )
    ids = await le.LoopEngineerService.list_scheduled_user_ids()
    assert user_id in ids


@pytest.mark.asyncio
async def test_digest_lines_pending_pipeline(loop_dir, monkeypatch):
    from app.application.services import search_pipeline as sp

    user_id = uuid4()
    run_id = str(uuid4())
    monkeypatch.setattr(sp, "_pipeline_root", lambda: loop_dir / "pipelines")
    root = loop_dir / "pipelines" / str(user_id)
    root.mkdir(parents=True)
    data = {
        "id": run_id,
        "user_id": str(user_id),
        "stage": "awaiting_shortlist",
        "jobs": [{"id": "a"}, {"id": "b"}],
        "preferences": {},
        "created_at": le._utc_now_iso(),
        "updated_at": le._utc_now_iso(),
    }
    (root / f"{run_id}.json").write_text(json.dumps(data), encoding="utf-8")

    svc = le.LoopEngineerService(db=None)  # type: ignore[arg-type]
    lines = svc.digest_lines(user_id)
    assert any("shortlist" in (l.get("text") or "").lower() for l in lines)
    assert any(l.get("run_id") == run_id for l in lines)
