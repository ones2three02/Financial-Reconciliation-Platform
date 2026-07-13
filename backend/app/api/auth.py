from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Dict

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(payload: LoginRequest) -> Dict[str, str]:
    # Default mock credentials for local dev
    if payload.username == "admin" and payload.password == "admin123":
        return {
            "access_token": "frp-session-token-admin-2026",
            "token_type": "bearer",
            "username": "admin"
        }
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="用户名或密码不正确，请重新输入"
    )
