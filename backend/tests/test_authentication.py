from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.routing import APIRoute

from backend.app.api.auth import LoginRequest, get_current_user, login
from backend.app.core.config import Settings, settings
from backend.app.main import app
from backend.app.models.auth import AppUser, UserSession
from backend.app.services import auth_service
from backend.app.services.auth_service import create_user


def test_password_and_session_token_are_not_stored_in_plaintext(db_session):
    user = create_user(
        db_session,
        username="finance_admin",
        password="correct-horse-battery-staple",
        role="admin",
    )
    db_session.commit()

    response = login(
        payload=LoginRequest(
            username="finance_admin",
            password="correct-horse-battery-staple",
        ),
        db=db_session,
    )

    assert response.access_token
    assert "correct-horse" not in user.password_hash
    session = db_session.query(UserSession).one()
    assert session.token_hash != response.access_token
    assert len(session.token_hash) == 64


def test_bearer_token_resolves_current_user(db_session):
    create_user(
        db_session,
        username="finance_admin",
        password="correct-horse-battery-staple",
        role="admin",
    )
    db_session.commit()
    response = login(
        payload=LoginRequest(
            username="finance_admin",
            password="correct-horse-battery-staple",
        ),
        db=db_session,
    )

    current = get_current_user(
        credentials=HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=response.access_token,
        ),
        db=db_session,
    )

    assert current.username == "finance_admin"


def test_expired_or_missing_session_is_rejected(db_session):
    user = AppUser(
        username="expired_user",
        password_hash="x",
        password_salt="y",
        role="viewer",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    db_session.add(
        UserSession(
            user_id=user.id,
            token_hash="a" * 64,
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
    )
    db_session.commit()

    with pytest.raises(HTTPException) as missing:
        get_current_user(credentials=None, db=db_session)
    assert missing.value.status_code == 401

    with pytest.raises(HTTPException) as expired:
        get_current_user(
            credentials=HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials="expired-token",
            ),
            db=db_session,
        )
    assert expired.value.status_code == 401


def test_repeated_failed_logins_temporarily_lock_account(db_session):
    user = create_user(
        db_session,
        username="lock_test",
        password="correct-horse-battery-staple",
        role="finance",
    )
    db_session.commit()

    for _ in range(5):
        with pytest.raises(HTTPException) as failure:
            login(
                payload=LoginRequest(username="lock_test", password="wrong-password"),
                db=db_session,
            )
        assert failure.value.status_code == 401

    db_session.refresh(user)
    assert user.failed_login_attempts == 5
    assert user.locked_until is not None
    with pytest.raises(HTTPException):
        login(
            payload=LoginRequest(
                username="lock_test",
                password="correct-horse-battery-staple",
            ),
            db=db_session,
        )


def test_business_api_requires_authentication_and_cors_is_allowlisted():
    business_routes = [
        route
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path.startswith("/api/v1/")
        and not route.path.startswith("/api/v1/auth/")
    ]
    assert business_routes
    for route in business_routes:
        dependency_names = {dependency.call.__name__ for dependency in route.dependant.dependencies}
        assert "get_current_user" in dependency_names, route.path

    from backend.app.core.config import settings

    assert settings.allowed_cors_origins == ["http://localhost:5173"]
    assert "*" not in settings.allowed_cors_origins


def test_desktop_cors_origins_are_only_added_in_desktop_mode():
    web_settings = Settings(
        CORS_ORIGINS="https://finance.example.com",
        FRP_DESKTOP=False,
    )
    desktop_settings = Settings(
        CORS_ORIGINS="https://finance.example.com",
        FRP_DESKTOP=True,
    )

    assert web_settings.allowed_cors_origins == ["https://finance.example.com"]
    assert desktop_settings.allowed_cors_origins == [
        "https://finance.example.com",
        "http://localhost:5174",
        "http://localhost:1420",
        "tauri://localhost",
        "http://tauri.localhost",
    ]


def test_application_has_no_automatic_database_or_default_user_startup_hook():
    assert app.router.on_startup == []


def test_desktop_setup_creates_the_only_first_admin(monkeypatch, db_session):
    from backend.app.api import auth as auth_api

    monkeypatch.setattr(settings, "FRP_DESKTOP", True)
    assert hasattr(auth_api, "desktop_setup_status"), "桌面首次初始化状态接口尚未实现"
    assert hasattr(auth_api, "setup_desktop_admin"), "桌面首次管理员创建接口尚未实现"
    assert auth_api.desktop_setup_status(db_session).setup_required is True

    response = auth_api.setup_desktop_admin(
        auth_api.DesktopSetupRequest(
            username="desktop_owner",
            password="correct-horse-battery-staple",
        ),
        db_session,
    )

    assert response.username == "desktop_owner"
    assert response.role == "admin"
    assert auth_api.desktop_setup_status(db_session).setup_required is False
    with pytest.raises(HTTPException) as duplicate:
        auth_api.setup_desktop_admin(
            auth_api.DesktopSetupRequest(
                username="second_owner",
                password="another-correct-password",
            ),
            db_session,
        )
    assert duplicate.value.status_code == 409


def test_insecure_seeded_admin_is_removed_but_changed_password_is_preserved(db_session):
    insecure = create_user(
        db_session,
        username="admin",
        password="admin_password_123",
        role="admin",
    )
    changed = create_user(
        db_session,
        username="changed_admin",
        password="a-user-selected-password",
        role="admin",
    )
    db_session.commit()

    assert hasattr(auth_service, "remove_insecure_seeded_admin"), "不安全默认账户清理尚未实现"
    assert auth_service.remove_insecure_seeded_admin(db_session) is True
    db_session.commit()

    assert db_session.get(AppUser, insecure.id) is None
    assert db_session.get(AppUser, changed.id) is not None


def test_desktop_mode_requires_launch_token_but_allows_cors_preflight():
    try:
        from backend.app.core.desktop_security import desktop_request_is_authorized
    except ModuleNotFoundError:
        raise AssertionError("桌面启动令牌校验尚未实现") from None

    desktop_settings = Settings(
        FRP_DESKTOP=True,
        FRP_DESKTOP_TOKEN="per-launch-secret",
    )
    assert desktop_request_is_authorized(desktop_settings, "GET", None) is False
    assert desktop_request_is_authorized(desktop_settings, "GET", "wrong") is False
    assert desktop_request_is_authorized(desktop_settings, "GET", "per-launch-secret") is True
    assert desktop_request_is_authorized(desktop_settings, "OPTIONS", None) is True
