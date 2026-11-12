"""Compatibilidad y modularización del flujo de autenticación de CASO16.

Este módulo expone un router reutilizable para integraciones futuras y evita
que la autenticación quede acoplada a un único archivo de entrada.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

import data_layer as dl
import security


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=120)


def get_current_user_optional(authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split("Bearer ", 1)[1].strip()
    try:
        payload = security.decode_access_token(token)
        return payload
    except Exception:
        return None


def build_auth_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1/auth")

    @router.post("/login")
    def login(payload: LoginRequest) -> dict[str, Any]:
        user = dl.authenticate_user(payload.username, payload.password)
        if not user:
            raise HTTPException(status_code=401, detail="Credenciales incorrectas o usuario inactivo")
        token = security.create_access_token({
            "sub": user["username"],
            "email": user["email"],
            "role": user["role"],
            "full_name": user["full_name"],
        })
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "username": user["username"],
                "email": user["email"],
                "role": user["role"],
                "full_name": user["full_name"],
            },
        }

    @router.get("/me")
    def get_current_user(current: dict[str, Any] | None = Depends(get_current_user_optional)) -> dict[str, Any]:
        if not current:
            raise HTTPException(status_code=401, detail="Token no suministrado o inválido")
        return current

    return router
