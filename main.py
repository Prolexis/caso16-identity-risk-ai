"""API REST versionada (/api/v1) de CASO16 — Identity Risk AI.

Provee endpoints para autenticación JWT, RBAC, gestión de hallazgos, tickets de remediación,
políticas de seguridad, bitácora de auditoría inmutable y explicabilidad heurística/IA.
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
import data_layer as dl
from sqlalchemy import select
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
    explain_finding_langflow,
    explain_finding_ai,
    finding_frame,
    init_db,
    policy_frame,
    role_frame,
    run_detection,
    trigger_n8n_pipeline,
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


def authenticated_user(current=Depends(get_current_user_optional)):
    if not current:
        raise HTTPException(401, 'Se requiere autenticación JWT')
    with dl.engine.connect() as conn:
        user = conn.execute(select(dl.users).where(dl.users.c.username == current.get('sub'), dl.users.c.active == True)).mappings().first()
    if not user:
        raise HTTPException(401, 'Usuario inactivo o inexistente')
    return dict(user)


def authorize_payload(payload, user, permission):
    dl.require_permission(user['role'], permission)
    if hasattr(payload, 'actor'): payload.actor = user['email']
    if hasattr(payload, 'role'): payload.role = user['role']
    if hasattr(payload, 'actor_role'): payload.actor_role = user['role']


@app.exception_handler(PermissionError)
async def permission_error(request: Request, exc: PermissionError):
    return JSONResponse(status_code=403, content={'detail': str(exc)})


@app.exception_handler(ValueError)
async def validation_error(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={'detail': str(exc)})


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
def create_new_user(payload: UserCreateRequest, current=Depends(authenticated_user)) -> dict[str, Any]:
    authorize_payload(payload, current, 'users')
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
        mask = frame.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False, regex=False)).any(axis=1)
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
def scan(payload: ScanRequest, current=Depends(authenticated_user)) -> dict[str, Any]:
    authorize_payload(payload, current, 'write')
    return run_detection(payload.actor, payload.role)


@app.patch("/api/v1/findings/{finding_id}")
def patch_finding(finding_id: int, payload: FindingUpdate, current=Depends(authenticated_user)) -> dict[str, str]:
    authorize_payload(payload, current, 'write')
    try:
        update_finding(finding_id, payload.status, payload.owner, payload.actor, payload.role, payload.comment)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "updated", "finding_id": str(finding_id)}


@app.post("/api/v1/findings/{finding_id}/explain")
def explain_finding(finding_id: int, payload: ScanRequest, current=Depends(authenticated_user)) -> dict[str, Any]:
    authorize_payload(payload, current, 'read')
    try:
        return explain_finding_langflow(finding_id, payload.actor, payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ==============================================================================
# ENDPOINTS DE ASISTENTE DE IA Y EXPLICABILIDAD (M07)
# ==============================================================================

@app.post("/api/v1/ai/explain/{finding_id}")
def explain_finding_heuristic(finding_id: int, current: dict[str, Any] | None = Depends(get_current_user_optional)) -> dict[str, Any]:
    actor = current["email"] if current else "anonymous@caso16.local"
    role = current["role"] if current else "Invitado"
    try:
        result = explain_finding_ai(finding_id)
        with dl.engine.begin() as conn:
            dl.audit_event(conn, actor, role, "explain_finding", f"finding:{finding_id}", "success", "Heurística determinista")
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/integrations/n8n/trigger", status_code=201)
def run_n8n_pipeline(payload: ScanRequest, current=Depends(authenticated_user)) -> dict[str, Any]:
    authorize_payload(payload, current, 'write')
    return trigger_n8n_pipeline(payload.actor, payload.role)


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
def create_new_ticket(payload: TicketCreateRequest, current=Depends(authenticated_user)) -> dict[str, Any]:
    authorize_payload(payload, current, 'remediate')
    ticket_id = create_ticket(
        payload.finding_id, payload.title, payload.description,
        payload.priority, payload.owner, payload.sla_days, payload.actor, payload.role
    )
    return {"status": "created", "ticket_id": ticket_id}


@app.patch("/api/v1/tickets/{ticket_id}")
def patch_ticket(ticket_id: str, payload: TicketUpdateRequest, current=Depends(authenticated_user)) -> dict[str, str]:
    authorize_payload(payload, current, 'remediate')
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
def patch_policy(policy_id: int, payload: PolicyUpdateRequest, current=Depends(authenticated_user)) -> dict[str, str]:
    authorize_payload(payload, current, 'policies')
    update_policy(policy_id, payload.threshold_value, payload.is_active, payload.actor, payload.role)
    return {"status": "updated", "policy_id": str(policy_id)}


@app.get("/api/v1/exceptions")
def get_exceptions() -> dict[str, Any]:
    frame = exception_frame()
    return {"items": frame.where(frame.notna(), None).to_dict(orient="records"), "total": len(frame)}


@app.post("/api/v1/exceptions", status_code=201)
def create_new_exception(payload: ExceptionCreateRequest, current=Depends(authenticated_user)) -> dict[str, Any]:
    authorize_payload(payload, current, 'policies')
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


from api_extensions import make_router
app.include_router(make_router(authenticated_user))
