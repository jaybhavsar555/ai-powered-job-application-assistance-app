"""Job packet service — filesystem unit tests."""

from __future__ import annotations

import json
from uuid import uuid4

import pytest

from app.application.services import job_packet as jp


@pytest.fixture()
def packet_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(jp, "_packets_root", lambda: tmp_path)
    return tmp_path


def test_jd_summary_truncates(packet_dir):
    svc = jp.JobPacketService(db=None)  # type: ignore[arg-type]
    long_desc = "x" * 500
    summary = svc._jd_summary({"description": long_desc})
    assert len(summary) <= 400
    assert summary.endswith("...")


def test_list_and_get_packet(packet_dir):
    user_id = uuid4()
    packet_id = str(uuid4())
    data = {
        "id": packet_id,
        "user_id": str(user_id),
        "status": "pending_review",
        "created_at": jp._utc_now_iso(),
        "updated_at": jp._utc_now_iso(),
        "job": {"title": "Engineer", "company": "Acme", "matchScore": 85},
    }
    path = jp._packet_path(user_id, packet_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")

    svc = jp.JobPacketService(db=None)  # type: ignore[arg-type]
    listed = svc.list_packets(user_id, status="pending_review")
    assert len(listed) == 1
    assert listed[0]["title"] == "Engineer"
    full = svc.get_packet(user_id, packet_id)
    assert full["job"]["company"] == "Acme"


def test_reject_packet(packet_dir):
    user_id = uuid4()
    packet_id = str(uuid4())
    data = {
        "id": packet_id,
        "status": "pending_review",
        "created_at": jp._utc_now_iso(),
        "job": {},
    }
    path = jp._packet_path(user_id, packet_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")

    svc = jp.JobPacketService(db=None)  # type: ignore[arg-type]
    out = svc.reject_packet(user_id, packet_id)
    assert out["packet"]["status"] == "rejected"
