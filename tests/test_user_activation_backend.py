from __future__ import annotations

import asyncio
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import endpoints
from app.core.security import get_current_active_user, get_current_admin_user, get_current_user
from app.db.models import RoleDB, UserDB
from app.main import app
from app.schemas.schemas import User
from app.services import account_pin_service, services


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class FakeDb:
    def __init__(self, user, role):
        self.user = user
        self.role = role
        self.committed = False
        self.closed = False
        self.refreshed = []

    def query(self, model):
        if model is UserDB:
            return FakeQuery(self.user)
        if model is RoleDB:
            return FakeQuery(self.role)
        raise AssertionError(f"Unexpected model query: {model}")

    def commit(self):
        self.committed = True

    def refresh(self, row):
        self.refreshed.append(row)

    def close(self):
        self.closed = True


def test_set_user_active_updates_db_flag_and_status(monkeypatch):
    user = SimpleNamespace(
        user_id=7,
        username="disabled.user",
        email="disabled@example.com",
        full_name="Disabled User",
        role_id=1,
        status="approved",
        is_active=True,
        pin_hash="",
        created_at=datetime.utcnow(),
        updated_at=None,
        rejection_reason=None,
    )
    role = SimpleNamespace(role_name="admin")
    fake_db = FakeDb(user=user, role=role)
    audit_calls = []

    monkeypatch.setattr(services, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(services, "log_action", lambda *args, **kwargs: audit_calls.append(kwargs))

    result = services.set_user_active(7, is_active=False, actor_user_id=99)

    assert result is not None
    assert fake_db.committed is True
    assert user.is_active is False
    assert user.status == "disabled"
    assert result.is_active is False
    assert audit_calls[0]["new_value"]["is_active"] is False


def test_get_pending_account_status_includes_is_active_false():
    user = SimpleNamespace(
        user_id=7,
        email="disabled@example.com",
        role_id=1,
        user_type=None,
        status="disabled",
        is_active=False,
        pin_hash="hashed",
        rejection_reason=None,
    )
    role = SimpleNamespace(role_id=1, role_name="manager")
    fake_db = FakeDb(user=user, role=role)

    payload = account_pin_service.get_pending_account_status(fake_db, 7)

    assert payload["user_id"] == 7
    assert payload["has_pin"] is True
    assert payload["status"] == "disabled"
    assert payload["is_active"] is False


def test_get_current_active_user_blocks_disabled_account():
    user = User(
        id=7,
        email="disabled@example.com",
        full_name="Disabled User",
        is_active=False,
        role="viewer",
        status="disabled",
        has_pin=True,
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(get_current_active_user(user))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "ACCOUNT_DISABLED"
    assert exc_info.value.detail["is_active"] is False


def test_login_returns_account_disabled_for_disabled_user(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(
        endpoints,
        "authenticate_user_by_username_or_email",
        lambda username_or_email, password: {
            "id": 7,
            "email": "disabled@example.com",
            "full_name": "Disabled User",
            "role": "viewer",
            "status": "disabled",
            "has_pin": True,
            "is_active": False,
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "disabled@example.com", "password": "secret"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ACCOUNT_DISABLED"
    assert response.json()["detail"]["is_active"] is False


def test_pending_status_returns_is_active_for_disabled_user(monkeypatch):
    client = TestClient(app)

    async def override_current_user():
        return User(
            id=7,
            email="disabled@example.com",
            full_name="Disabled User",
            is_active=False,
            role="viewer",
            status="disabled",
            has_pin=True,
        )

    app.dependency_overrides[get_current_user] = override_current_user
    monkeypatch.setattr(
        account_pin_service,
        "get_pending_account_status",
        lambda db, user_id: {
            "user_id": user_id,
            "email": "disabled@example.com",
            "role": "viewer",
            "status": "disabled",
            "has_pin": True,
            "is_active": False,
            "rejection_reason": None,
        },
    )

    try:
        response = client.get("/api/v1/auth/pending/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert response.json()["status"] == "disabled"


def test_admin_activate_endpoint_sets_user_active_true(monkeypatch):
    client = TestClient(app)
    captured = {}

    async def override_admin_user():
        return User(
            id=99,
            email="admin@example.com",
            full_name="Admin",
            is_active=True,
            role="admin",
            is_admin=True,
            status="approved",
            has_pin=True,
        )

    def fake_set_user_active(user_id, is_active, actor_user_id=None):
        captured["user_id"] = user_id
        captured["is_active"] = is_active
        captured["actor_user_id"] = actor_user_id
        return SimpleNamespace(status="approved")

    app.dependency_overrides[get_current_admin_user] = override_admin_user
    monkeypatch.setattr(endpoints.services, "set_user_active", fake_set_user_active)

    try:
        response = client.patch("/api/v1/admin/users/123/activate")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["user_id"] == 123
    assert response.json()["is_active"] is True
    assert captured["user_id"] == 123
    assert captured["is_active"] is True
    assert captured["actor_user_id"] == 99
