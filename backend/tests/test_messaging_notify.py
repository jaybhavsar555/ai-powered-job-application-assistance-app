"""Telegram link codes + messaging helpers."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.infrastructure.messaging import telegram_link as tl


@pytest.fixture()
def link_store(tmp_path, monkeypatch):
    monkeypatch.setattr(tl, "_store_path", lambda: tmp_path / "codes.json")
    return tmp_path


def test_create_and_consume_link_code(link_store):
    user_id = uuid4()
    code = tl.create_link_code(user_id, ttl_minutes=60)
    assert len(code) == 8
    linked = tl.consume_link_code(code)
    assert linked == str(user_id)
    assert tl.consume_link_code(code) is None


def test_consume_unknown_code(link_store):
    assert tl.consume_link_code("ZZZZZZZZ") is None
