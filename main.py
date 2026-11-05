"""API REST versionada (/api/v1) de CASO16 — Identity Risk AI.

Provee endpoints para autenticación JWT, RBAC, gestión de hallazgos, tickets de remediación,
políticas de seguridad, bitácora de auditoría inmutable y explicabilidad heurística/IA.
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import security
from data_layer import (
    account_frame,
    api_health,
    audit_frame,
    authenticate_user,
    create_exception,
    create_ticket,
    create_user,
    dashboard_metrics,
    directory_source_frame,
    exception_frame,
    explain_finding_ai,
    finding_frame,
    init_db,
    policy_frame,
    role_frame,
    run_detection,
    system_health_metrics,
    ticket_frame,
    update_finding,
    update_policy,
    update_ticket,
    user_frame,
)

app = FastAPI(
    title="CASO16 API — Identity Risk AI",
    version="1.0.0",
    description="API empresarial de ciberseguridad para detección determinista de cuentas huérfanas, privilegios excesivos y gobierno de identidades Active Directory."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8501", "*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


# ==============================================================================
# ESQUEMAS PYDANTIC
# ==============================================================================

class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=120)


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=5, max_length=180)
    password: str = Field(min_length=4, max_length=120)
    full_name: str = Field(min_length=2, max_length=180)
    role: str = Field(default="Analista de ciberseguridad", max_length=80)
    actor: str = Field(default="admin@demo.local", max_length=160)
    actor_role: str = Field(default="Superadministrador", max_length=100)


class ScanRequest(BaseModel):
    actor: str = Field(default="api@demo.local", max_length=160)
    role: str = Field(default="Analista de ciberseguridad", max_length=100)


class FindingUpdate(BaseModel):
    status: str = Field(min_length=2, max_length=40)
    owner: str | None = Field(default=None, max_length=160)
    comment: str = Field(default="", max_length=1000)
    actor: str = Field(default="api@demo.local", max_length=160)
    role: str = Field(default="Analista de ciberseguridad", max_length=100)


class TicketCreateRequest(BaseModel):
    finding_id: int | None = Field(default=None)
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(min_length=3)
    priority: str = Field(default="Media", max_length=20)
    owner: str = Field(default="remediator@demo.local", max_length=160)
    sla_days: int = Field(default=7, ge=1, le=90)
    actor: str = Field(default="api@demo.local", max_length=160)
    role: str = Field(default="Analista de ciberseguridad", max_length=100)


class TicketUpdateRequest(BaseModel):
    status: str = Field(min_length=2, max_length=30)
    owner: str | None = Field(default=None, max_length=160)
    resolution_notes: str | None = Field(default=None, max_length=2000)
    actor: str = Field(default="api@demo.local", max_length=160)
    role: str = Field(default="Responsable de remediación", max_length=100)


class PolicyUpdateRequest(BaseModel):
    threshold_value: int = Field(ge=0, le=1000)
    is_active: bool = Field(default=True)
    actor: str = Field(default="admin@demo.local", max_length=160)
    role: str = Field(default="Superadministrador", max_length=100)


class ExceptionCreateRequest(BaseModel):
    account_id: int
    rule_id: str = Field(min_length=3, max_length=10)
    justification: str = Field(min_length=5, max_length=1000)
    approved_by: str = Field(default="security@demo.local", max_length=160)
    days_valid: int = Field(default=30, ge=1, le=365)
    actor: str = Field(default="security@demo.local", max_length=160)
    role: str = Field(default="Administrador de seguridad", max_length=100)


# ==============================================================================
# SEGURIDAD Y CONTROL DE SESIÓN
# ==============================================================================

def get_current_user_optional(authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split("Bearer ")[1].strip()
    try:
        payload = security.decode_access_token(token)
        return payload
    except Exception:
        return None


# Base de datos inicializada al cargar data_layer


# ==============================================================================
# ENDPOINTS DE AUTENTICACIÓN Y USUARIOS (M01, M02)
# ==============================================================================

@app.post("/api/v1/auth/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    user = authenticate_user(payload.username, payload.password)
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
        }
    }


@app.get("/api/v1/auth/me")
def get_current_user(current: dict[str, Any] | None = Depends(get_current_user_optional)) -> dict[str, Any]:
    if not current:
        raise HTTPException(status_code=401, detail="Token no suministrado o inválido")
    return current


@app.get("/api/v1/users")
def get_users() -> dict[str, Any]:
    frame = user_frame().drop(columns=["hashed_password"], errors="ignore")
    return {"items": frame.where(frame.notna(), None).to_dict(orient="records"), "total": len(frame)}


@app.post("/api/v1/users", status_code=201)
def create_new_user(payload: UserCreateRequest) -> dict[str, Any]:
    try:
        created = create_user(
            payload.username, payload.email, payload.password, payload.full_name,
            payload.role, payload.actor, payload.actor_role
        )
        return {"status": "created", "user": created}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/roles")
def get_roles() -> dict[str, Any]:
    frame = role_frame()
    return {"items": frame.where(frame.notna(), None).to_dict(orient="records"), "total": len(frame)}


# ==============================================================================
# ENDPOINTS DE SALUD Y MONITOREO (M15)
# ==============================================================================

@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    return api_health()


@app.get("/api/v1/health/system")
def health_system() -> dict[str, Any]:
    return system_health_metrics()


@app.get("/api/v1/dashboard")
def dashboard() -> dict[str, Any]:
    return dashboard_metrics()


# ==============================================================================
# ENDPOINTS DE INVENTARIO Y HALLAZGOS (M05, M06, M08)
# ==============================================================================

@app.get("/api/v1/accounts")
def accounts(limit: int = Query(default=100, ge=1, le=1000), search: str | None = None) -> dict[str, Any]:
    frame = account_frame()
    if search:
        mask = frame.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        frame = frame[mask]
    frame = frame.head(limit).where(frame.notna(), None)
    return {"items": frame.to_dict(orient="records"), "total": int(len(frame))}


@app.get("/api/v1/findings")
def findings(status: str | None = None, severity: str | None = None, limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    frame = finding_frame()
    if status:
        frame = frame[frame["status"] == status]
    if severity:
        frame = frame[frame["severity"] == severity]
    frame = frame.head(limit).where(frame.notna(), None)
    return {"items": frame.to_dict(orient="records"), "total": int(len(frame))}


@app.post("/api/v1/scans", status_code=201)
def scan(payload: ScanRequest) -> dict[str, Any]:
    return run_detection(payload.actor, payload.role)


@app.patch("/api/v1/findings/{finding_id}")
def patch_finding(finding_id: int, payload: FindingUpdate) -> dict[str, str]:
    try:
        update_finding(finding_id, payload.status, payload.owner, payload.actor, payload.role, payload.comment)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "updated", "finding_id": str(finding_id)}


# ==============================================================================
# ENDPOINTS DE ASISTENTE DE IA Y EXPLICABILIDAD (M07)
# ==============================================================================

@app.post("/api/v1/ai/explain/{finding_id}")
def explain_finding(finding_id: int) -> dict[str, Any]:
    try:
        return explain_finding_ai(finding_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ==============================================================================
# ENDPOINTS DE GESTIÓN DE TICKETS Y REMEDIACIÓN (M09)
# ==============================================================================

@app.get("/api/v1/tickets")
def get_tickets(status: str | None = None, priority: str | None = None) -> dict[str, Any]:
    frame = ticket_frame()
    if status:
        frame = frame[frame["status"] == status]
    if priority:
        frame = frame[frame["priority"] == priority]
    frame = frame.where(frame.notna(), None)
    return {"items": frame.to_dict(orient="records"), "total": len(frame)}


@app.post("/api/v1/tickets", status_code=201)
def create_new_ticket(payload: TicketCreateRequest) -> dict[str, Any]:
    ticket_id = create_ticket(
        payload.finding_id, payload.title, payload.description,
        payload.priority, payload.owner, payload.sla_days, payload.actor, payload.role
    )
    return {"status": "created", "ticket_id": ticket_id}


@app.patch("/api/v1/tickets/{ticket_id}")
def patch_ticket(ticket_id: str, payload: TicketUpdateRequest) -> dict[str, str]:
    try:
        update_ticket(ticket_id, payload.status, payload.owner, payload.resolution_notes, payload.actor, payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "updated", "ticket_id": ticket_id}


# ==============================================================================
# ENDPOINTS DE FUENTES DE DIRECTORIO Y POLÍTICAS (M04, M14)
# ==============================================================================

@app.get("/api/v1/directories")
def get_directories() -> dict[str, Any]:
    frame = directory_source_frame()
    return {"items": frame.where(frame.notna(), None).to_dict(orient="records"), "total": len(frame)}


@app.get("/api/v1/policies")
def get_policies() -> dict[str, Any]:
    frame = policy_frame()
    return {"items": frame.where(frame.notna(), None).to_dict(orient="records"), "total": len(frame)}


@app.patch("/api/v1/policies/{policy_id}")
def patch_policy(policy_id: int, payload: PolicyUpdateRequest) -> dict[str, str]:
    update_policy(policy_id, payload.threshold_value, payload.is_active, payload.actor, payload.role)
    return {"status": "updated", "policy_id": str(policy_id)}


@app.get("/api/v1/exceptions")
def get_exceptions() -> dict[str, Any]:
    frame = exception_frame()
    return {"items": frame.where(frame.notna(), None).to_dict(orient="records"), "total": len(frame)}


@app.post("/api/v1/exceptions", status_code=201)
def create_new_exception(payload: ExceptionCreateRequest) -> dict[str, Any]:
    exc_id = create_exception(
        payload.account_id, payload.rule_id, payload.justification,
        payload.approved_by, payload.days_valid, payload.actor, payload.role
    )
    return {"status": "created", "exception_id": exc_id}


# ==============================================================================
# ENDPOINTS DE AUDITORÍA (M03)
# ==============================================================================

@app.get("/api/v1/audit")
def get_audit_trail(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    frame = audit_frame().head(limit)
    return {"items": frame.where(frame.notna(), None).to_dict(orient="records"), "total": len(frame)}
