from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.app.core.db import get_db
from backend.app.models.auth import AppUser
from backend.app.services.auth_service import (
    authenticate_user,
    create_session,
    revoke_session,
    user_for_token,
)


router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


class CurrentUserResponse(BaseModel):
    username: str
    role: str


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AppUser:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise HTTPException(status_code=401, detail="需要登录", headers={"WWW-Authenticate": "Bearer"})
    user = user_for_token(db, credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="登录已失效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(current_user: AppUser = Depends(get_current_user)) -> AppUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


def require_finance(current_user: AppUser = Depends(get_current_user)) -> AppUser:
    if current_user.role not in {"admin", "finance"}:
        raise HTTPException(status_code=403, detail="需要财务操作权限")
    return current_user


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        db.commit()
        raise HTTPException(status_code=401, detail="用户名或密码不正确")
    token, _ = create_session(db, user)
    db.commit()
    return LoginResponse(
        access_token=token,
        username=user.username,
        role=user.role,
    )


@router.get("/me", response_model=CurrentUserResponse)
def current_user(current: AppUser = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(username=current.username, role=current.role)


@router.post("/logout", status_code=204)
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if credentials is None:
        raise HTTPException(status_code=401, detail="需要登录")
    revoke_session(db, credentials.credentials)
    db.commit()
    return None
