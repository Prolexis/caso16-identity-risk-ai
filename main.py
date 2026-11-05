"""API REST mínima versionada para integrar el motor CASO16 con otros clientes."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from data_layer import (
    account_frame,
    api_health,
    dashboard_metrics,
    explain_finding_langflow,
    finding_frame,
    init_db,
    run_detection,
    trigger_n8n_pipeline,
    update_finding,
)

app = FastAPI(title="CASO16 API", version="0.1.0", description="API de demostración para detección de cuentas huérfanas y privilegios excesivos")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8501"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)


class ScanRequest(BaseModel):
    actor: str = Field(default="api@demo.local", max_length=160)
    role: str = Field(default="Analista de ciberseguridad", max_length=100)


class FindingUpdate(BaseModel):
    status: str = Field(min_length=2, max_length=40)
    owner: str | None = Field(default=None, max_length=160)
    comment: str = Field(default="", max_length=1000)
    actor: str = Field(default="api@demo.local", max_length=160)
    role: str = Field(default="Analista de ciberseguridad", max_length=100)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    return api_health()


@app.get("/api/v1/dashboard")
def dashboard() -> dict[str, Any]:
    return dashboard_metrics()


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


@app.post("/api/v1/findings/{finding_id}/explain")
def explain_finding(finding_id: int, payload: ScanRequest) -> dict[str, Any]:
    try:
        return explain_finding_langflow(finding_id, payload.actor, payload.role)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/integrations/n8n/trigger", status_code=201)
def run_n8n_pipeline(payload: ScanRequest) -> dict[str, Any]:
    return trigger_n8n_pipeline(payload.actor, payload.role)

