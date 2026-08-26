"""Search pipeline — unit tests (filesystem + stage gates, no live boards)."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.application.services import search_pipeline as sp


@pytest.fixture()
def pipeline_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sp, "_pipeline_root", lambda: tmp_path)
    return tmp_path


def test_stages_meta():
    ids = [s["id"] for s in sp.STAGES]
    assert "awaiting_shortlist" in ids
    assert "awaiting_execute" in ids
    assert all(isinstance(s.get("needs_approval"), bool) for s in sp.STAGES)


def test_approve_shortlist_gate(pipeline_dir):
    user_id = uuid4()
    run_id = str(uuid4())
    data = {
        "id": run_id,
        "user_id": str(user_id),
        "stage": "awaiting_shortlist",
        "jobs": [
            {"id": "a", "title": "A", "shortlisted": False},
            {"id": "b", "title": "B", "shortlisted": False},
        ],
        "history": [],
    }
    path = sp._run_path(user_id, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")

    svc = sp.SearchPipelineService(db=None)  # type: ignore[arg-type]
    out = svc.approve_shortlist(user_id, run_id, ["a"])
    assert out["stage"] == "awaiting_evaluate"
    by_id = {j["id"]: j for j in out["jobs"]}
    assert by_id["a"]["shortlisted"] is True
    assert by_id["b"]["shortlisted"] is False
    assert by_id["a"]["evaluation"]["global_score"] >= 1.0


def test_approve_shortlist_requires_selection(pipeline_dir):
    user_id = uuid4()
    run_id = str(uuid4())
    data = {
        "id": run_id,
        "user_id": str(user_id),
        "stage": "awaiting_shortlist",
        "jobs": [{"id": "a", "shortlisted": False}],
        "history": [],
    }
    path = sp._run_path(user_id, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    svc = sp.SearchPipelineService(db=None)  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as ei:
        svc.approve_shortlist(user_id, run_id, [])
    assert ei.value.status_code == 400


def test_wrong_stage_rejected(pipeline_dir):
    user_id = uuid4()
    run_id = str(uuid4())
    data = {
        "id": run_id,
        "user_id": str(user_id),
        "stage": "done",
        "jobs": [],
        "history": [],
    }
    path = sp._run_path(user_id, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    svc = sp.SearchPipelineService(db=None)  # type: ignore[arg-type]
    with pytest.raises(HTTPException) as ei:
        svc.approve_shortlist(user_id, run_id, ["x"])
    assert ei.value.status_code == 400
