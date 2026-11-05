"""Módulo de seguridad, autenticación JWT y hashing de contraseñas para CASO16."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

SECRET_KEY = os.getenv("CASO16_SECRET_KEY", "caso16-enterprise-jwt-super-secret-key-2026-sha256")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 horas
UTC = timezone.utc


def hash_password(plain_password: str) -> str:
    """Genera hash seguro PBKDF2-HMAC-SHA256 con salt aleatorio."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 120_000)
    return f"pbkdf2:sha256:120000${base64.b64encode(salt).decode('ascii')}${base64.b64encode(dk).decode('ascii')}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una contraseña en texto plano coincide con el hash almacenado."""
    try:
        if not hashed_password.startswith("pbkdf2:sha256:"):
            # Compatibilidad simple de fallback en caso de hash legado
            return hmac.compare_digest(plain_password, hashed_password)
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        _, salt_b64, hash_b64 = parts
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected_dk = base64.b64decode(hash_b64.encode("ascii"))
        actual_dk = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 120_000)
        return hmac.compare_digest(expected_dk, actual_dk)
    except Exception:
        return False


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Genera un token JWT firmado."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.now(UTC)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica y valida un token JWT."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("El token de sesión ha expirado")
    except jwt.InvalidTokenError:
        raise ValueError("Token de autenticación no válido")

