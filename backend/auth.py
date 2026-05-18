from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from . import security
from .config import ADMIN_EMAIL, ADMIN_PASSWORD
from .database import SessionLocal, get_session
from .models import User


log = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def ensure_admin_user() -> None:
    if not ADMIN_PASSWORD:
        log.warning("ADMIN_PASSWORD não configurada; admin não foi criado/atualizado.")
        return
    with SessionLocal() as s:
        u = s.query(User).filter(User.email == ADMIN_EMAIL).one_or_none()
        if u is None:
            u = User(
                email=ADMIN_EMAIL,
                password_hash=security.hash_password(ADMIN_PASSWORD),
                is_admin=True,
            )
            s.add(u)
            log.info("Admin %s criado.", ADMIN_EMAIL)
        else:
            u.password_hash = security.hash_password(ADMIN_PASSWORD)
            u.is_admin = True
            log.info("Admin %s atualizado.", ADMIN_EMAIL)
        s.commit()


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth.split(" ", 1)[1].strip()
    return request.cookies.get("access_token")


def require_user(request: Request, db: Session = Depends(get_session)) -> User:
    token = _extract_token(request)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autenticado")
    payload = security.decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido")
    user = db.query(User).filter(User.id == int(payload["sub"])).one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário não encontrado")
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_session)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user is None or not security.verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email ou senha incorretos")
    token = security.create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "email": user.email, "is_admin": user.is_admin},
    )


@router.get("/me")
def me(user: User = Depends(require_user)) -> dict:
    return {"id": user.id, "email": user.email, "is_admin": user.is_admin}
