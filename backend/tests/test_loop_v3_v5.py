"""Portfolio export + extension apply queue tests."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.application.services import portfolio_export as pe
from app.application.services import extension_apply_queue as eq


@pytest.fixture()
def portfolio_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(pe, "_portfolio_root", lambda: tmp_path)
    return tmp_path


@pytest.fixture()
def queue_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(eq, "_queue_path", lambda uid: tmp_path / f"{uid}.json")
    return tmp_path


def test_portfolio_export(portfolio_dir):
    user_id = uuid4()
    packet = {
        "id": "pkt-1",
        "job": {"title": "Engineer", "company": "Acme"},
        "tailored_resume": {
            "summary": "Built scalable APIs.",
            "tailored_bullets": ["Shipped features end-to-end."],
            "added_keywords": ["Python", "FastAPI"],
        },
        "company_research": {"summary": "Acme builds fintech tools."},
    }
    svc = pe.PortfolioExportService()
    out = svc.export_from_packet(user_id, packet, user_email="dev@example.com")
    assert out["ok"] is True
    html = svc.read_html(user_id)
    assert html and "Built scalable APIs" in html


def test_extension_apply_queue(queue_dir):
    user_id = uuid4()
    entry = eq.enqueue(
        user_id,
        application_id="app-1",
        job_id="job-1",
        url="https://boards.greenhouse.io/acme/jobs/1",
        company="Acme",
        title="Engineer",
        packet_id="pkt-1",
    )
    assert entry["status"] == "pending"
    pending = eq.list_queue(user_id)
    assert len(pending) == 1
    assert eq.mark_done(user_id, "app-1")
    assert len(eq.list_queue(user_id)) == 0
