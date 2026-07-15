import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.models.auth import AppUser, UserSession


PASSWORD_MIN_LENGTH = 12
SESSION_TTL = timedelta(hours=8)
MAX_FAILED_LOGINS = 5
LOCKOUT_DURATION = timedelta(minutes=15)
DUMMY_SALT_HEX = "0" * 32


def _password_digest(password: str, salt_hex: str) -> str:
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=bytes.fromhex(salt_hex),
        n=2**14,
        r=8,
        p=1,
        dklen=64,
    ).hex()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user(
    db: Session,
    *,
    username: str,
    password: str,
    role: str,
) -> AppUser:
    clean_username = username.strip()
    clean_role = role.strip()
    if not clean_username:
        raise ValueError("用户名不能为空")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"密码长度不能少于 {PASSWORD_MIN_LENGTH} 位")
    if clean_role not in {"admin", "finance", "viewer"}:
        raise ValueError(f"不支持的角色: {clean_role}")
    if db.query(AppUser).filter(AppUser.username == clean_username).first() is not None:
        raise ValueError("用户名已经存在")

    salt_hex = secrets.token_bytes(16).hex()
    user = AppUser(
        username=clean_username,
        password_salt=salt_hex,
        password_hash=_password_digest(password, salt_hex),
        role=clean_role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def remove_insecure_seeded_admin(db: Session) -> bool:
    user = db.query(AppUser).filter(AppUser.username == "admin").first()
    if user is None:
        return False
    insecure_hash = _password_digest("admin_password_123", user.password_salt)
    if not hmac.compare_digest(insecure_hash, user.password_hash):
        return False
    db.query(UserSession).filter(UserSession.user_id == user.id).delete()
    db.delete(user)
    db.flush()
    return True


def authenticate_user(db: Session, username: str, password: str) -> AppUser | None:
    user = (
        db.query(AppUser)
        .filter(AppUser.username == username.strip(), AppUser.is_active.is_(True))
        .first()
    )
    if user is None:
        _password_digest(password, DUMMY_SALT_HEX)
        return None
    now = datetime.now(UTC)
    locked_until = user.locked_until
    if locked_until is not None:
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=UTC)
        if locked_until > now:
            _password_digest(password, user.password_salt)
            return None
    candidate = _password_digest(password, user.password_salt)
    if not hmac.compare_digest(candidate, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= MAX_FAILED_LOGINS:
            user.locked_until = now + LOCKOUT_DURATION
        db.flush()
        return None
    user.failed_login_attempts = 0
    user.locked_until = None
    db.flush()
    return user


def create_session(db: Session, user: AppUser) -> tuple[str, UserSession]:
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    session = UserSession(
        user_id=user.id,
        token_hash=_token_hash(token),
        expires_at=now + SESSION_TTL,
    )
    user.last_login_at = now
    db.add(session)
    db.flush()
    return token, session


def user_for_token(db: Session, token: str) -> AppUser | None:
    session = (
        db.query(UserSession)
        .filter(
            UserSession.token_hash == _token_hash(token),
            UserSession.revoked_at.is_(None),
        )
        .first()
    )
    if session is None:
        return None
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= datetime.now(UTC):
        return None
    user = db.get(AppUser, session.user_id)
    return user if user is not None and user.is_active else None


def revoke_session(db: Session, token: str) -> bool:
    session = (
        db.query(UserSession)
        .filter(
            UserSession.token_hash == _token_hash(token),
            UserSession.revoked_at.is_(None),
        )
        .first()
    )
    if session is None:
        return False
    session.revoked_at = datetime.now(UTC)
    db.flush()
    return True
