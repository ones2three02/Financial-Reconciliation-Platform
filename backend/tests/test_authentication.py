from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.routing import APIRoute

from backend.app.api.auth import LoginRequest, get_current_user, login
from backend.app.models.auth import AppUser, UserSession
from backend.app.services.auth_service import create_user
from backend.app.main import app


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
