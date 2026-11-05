"""Persistencia y motor determinista de CASO16.

La aplicación usa PostgreSQL cuando DATABASE_URL está configurada (por ejemplo en
Docker Compose) y SQLite solo como fallback local explícito para una demo sin
infraestructura externa. Los datos de seed están marcados como sintéticos.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Integer, MetaData, String, Table, Text, and_,
    create_engine, func, insert, select, update
)

UTC = timezone.utc
NOW = datetime.now(UTC)
DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/caso16.db")
if DB_URL.startswith("sqlite"):
    Path("data").mkdir(exist_ok=True)

engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
# Declarative tables kept deliberately small for the runnable demo.
metadata = MetaData()
accounts = Table(
    "directory_accounts", metadata,
    Column("id", Integer, primary_key=True),
    Column("external_id", String(120), nullable=False, unique=True),
    Column("username", String(120), nullable=False),
    Column("display_name", String(180), nullable=False),
    Column("email", String(180)),
    Column("account_type", String(30), nullable=False),
    Column("source", String(80), nullable=False),
    Column("active", Boolean, nullable=False, default=True),
    Column("is_admin", Boolean, nullable=False, default=False),
    Column("justification_verified", Boolean, nullable=False, default=False),
    Column("is_duplicate", Boolean, nullable=False, default=False),
    Column("password_never_expires", Boolean, nullable=False, default=False),
    Column("privileged_roles", Text, nullable=False, default=""),
    Column("last_activity", Date),
    Column("review_at", Date),
    Column("risk_score", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
findings = Table(
    "findings", metadata,
    Column("id", Integer, primary_key=True),
    Column("account_id", Integer, nullable=False),
    Column("rule_id", String(10), nullable=False),
    Column("title", String(240), nullable=False),
    Column("severity", String(20), nullable=False),
    Column("evidence_state", String(30), nullable=False),
    Column("status", String(30), nullable=False, default="Detectado"),
    Column("rationale", Text, nullable=False),
    Column("evidence", Text, nullable=False),
    Column("risk_score", Integer, nullable=False, default=0),
    Column("owner", String(160)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)
runs = Table(
    "detection_runs", metadata,
    Column("id", String(40), primary_key=True),
    Column("source", String(80), nullable=False),
    Column("mode", String(30), nullable=False),
    Column("status", String(30), nullable=False),
    Column("accounts_processed", Integer, nullable=False, default=0),
    Column("findings_created", Integer, nullable=False, default=0),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True)),
)
audit_logs = Table(
    "audit_logs", metadata,
    Column("id", Integer, primary_key=True),
    Column("actor", String(160), nullable=False),
    Column("role", String(80), nullable=False),
    Column("action", String(100), nullable=False),
    Column("resource", String(180), nullable=False),
    Column("result", String(30), nullable=False),
    Column("details", Text, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
)

RULES = {
    "R01": ("Inactividad prolongada", "Cuenta sin actividad durante 90 días o más"),
    "R02": ("Privilegio administrativo sin justificación", "Cuenta admin sin justificación verificable"),
    "R03": ("Cuenta administrativa duplicada", "Posible identidad administrativa redundante"),
    "R04": ("Contraseña de servicio no expira", "Cuenta de servicio con contraseña eterna"),
    "R05": ("Privilegios inconsistentes", "Privilegios fuera de la política configurada"),
    "R06": ("Riesgo alto sin revisión", "Cuenta de riesgo elevado sin revisión reciente"),
}
SEVERITY_BY_RULE = {"R01": "Medio", "R02": "Alto", "R03": "Medio", "R04": "Alto", "R05": "Crítico", "R06": "Alto"}
ALLOWED_PRIVILEGES = {"Domain Users", "Helpdesk", "ReadOnly"}


def init_db() -> None:
    metadata.create_all(engine)
    with engine.begin() as conn:
        count = conn.execute(select(func.count()).select_from(accounts)).scalar_one()
        if count == 0:
            seed_demo(conn)
            audit_event(conn, "system", "system", "seed_demo", "directory_accounts", "success", "Datos sintéticos iniciales cargados")


def seed_demo(conn=None) -> None:
    rows = [
        ("demo-001", "ana.garcia", "Ana García", "ana.garcia@demo.local", "user", "Demo LDAP", True, False, True, False, False, "Domain Users", 18, 12, None),
        ("demo-002", "bruno.admin", "Bruno Admin", "bruno.admin@demo.local", "admin", "Demo LDAP", True, True, False, False, False, "Domain Admins|Server Admins", 130, None, 110),
        ("demo-003", "carla.service", "svc-backup", "svc-backup@demo.local", "service", "Demo LDAP", True, False, True, False, True, "Backup Operators|ReadOnly", 4, 160, None),
        ("demo-004", "diego.ops", "Diego Operaciones", "diego.ops@demo.local", "admin", "Demo LDAP", True, True, True, True, False, "Helpdesk|ReadOnly", 35, 9, 9),
        ("demo-005", "svc-reports", "svc-reports", "svc-reports@demo.local", "service", "Demo LDAP", True, False, True, False, True, "Report Writers", 200, None, 200),
        ("demo-006", "elena.user", "Elena Usuario", "elena.user@demo.local", "user", "Demo AD", True, False, True, False, False, "Domain Users", None, None, None),
        ("demo-007", "francisco.admin", "Francisco Admin", "francisco.admin@demo.local", "admin", "Demo AD", True, True, False, True, False, "Domain Admins", 95, 80, None),
        ("demo-008", "grace.audit", "Grace Auditor", "grace.audit@demo.local", "user", "Demo AD", False, False, True, False, False, "ReadOnly", 20, 3, 3),
        ("demo-009", "hugo.dev", "Hugo Desarrollo", "hugo.dev@demo.local", "user", "Demo AD", True, False, True, False, False, "Developers|ReadOnly", 10, 8, None),
        ("demo-010", "iris.legacy", "Iris Legacy", "iris.legacy@demo.local", "service", "Demo LDAP", True, False, False, False, True, "Legacy Admin", 300, None, None),
        ("demo-011", "julia.admin", "Julia Admin", "julia.admin@demo.local", "admin", "Demo AD", True, True, True, False, False, "Helpdesk", 22, 20, None),
        ("demo-012", "kevin.user", "Kevin Usuario", "kevin.user@demo.local", "user", "Demo AD", True, False, True, False, False, "Domain Users", 2, 2, 2),
    ]
    target = conn or engine.begin()
    close = conn is None
    try:
        for ext, user, name, email, typ, source, active, admin, justified, duplicate, never_exp, roles, activity_days, review_days, _unused in rows:
            last = None if activity_days is None else (date.today() - timedelta(days=activity_days))
            review = None if review_days is None else (date.today() - timedelta(days=review_days))
            target.execute(insert(accounts).values(
                external_id=ext, username=user, display_name=name, email=email, account_type=typ,
                source=source, active=active, is_admin=admin, justification_verified=justified,
                is_duplicate=duplicate, password_never_expires=never_exp, privileged_roles=roles,
                last_activity=last, review_at=review, risk_score=0, created_at=datetime.now(UTC),
            ))
    finally:
        if close:
            target.commit()
            target.close()


def audit_event(conn, actor: str, role: str, action: str, resource: str, result: str, details: str) -> None:
    conn.execute(insert(audit_logs).values(
        actor=actor, role=role, action=action, resource=resource, result=result,
        details=details[:1000], occurred_at=datetime.now(UTC)
    ))


def df(table: Table, where=None, order_by=None) -> pd.DataFrame:
    stmt = select(table)
    if where is not None:
        stmt = stmt.where(where)
    if order_by is not None:
        stmt = stmt.order_by(order_by)
    with engine.connect() as conn:
        return pd.read_sql(stmt, conn)


def compute_score(row: dict[str, Any]) -> int:
    score = 0
    if row.get("is_admin"): score += 25
    last = row.get("last_activity")
    if last is None: score += 30
    else:
        if isinstance(last, str): last = date.fromisoformat(last[:10])
        score += min(30, max(0, (date.today() - last).days // 5))
    if row.get("account_type") == "service": score += 20
    if row.get("password_never_expires"): score += 15
    roles = str(row.get("privileged_roles") or "")
    if any(role.strip() not in ALLOWED_PRIVILEGES for role in roles.split("|") if role.strip()): score += 25
    review = row.get("review_at")
    if review is None: score += 10
    return min(100, score)


def classify_risk(score: int) -> str:
    return "Crítico" if score >= 80 else "Alto" if score >= 60 else "Medio" if score >= 35 else "Bajo"


def run_detection(actor: str = "analyst@demo.local", role: str = "Analista de ciberseguridad") -> dict[str, Any]:
    init_db()
    run_id = "run-" + uuid.uuid4().hex[:12]
    started = datetime.now(UTC)
    with engine.begin() as conn:
        conn.execute(insert(runs).values(id=run_id, source="Demo LDAP + Demo AD", mode="deterministic", status="running", accounts_processed=0, findings_created=0, started_at=started))
        account_rows = [dict(r._mapping) for r in conn.execute(select(accounts)).fetchall()]
        created = 0
        for row in account_rows:
            score = compute_score(row)
            conn.execute(update(accounts).where(accounts.c.id == row["id"]).values(risk_score=score))
            candidates: list[tuple[str, str, str, str]] = []
            last = row["last_activity"]
            inactive_days = None if last is None else (date.today() - last).days
            if last is None:
                candidates.append(("R01", "potential", f"No existe evidencia de last activity en el origen {row['source']}", "last_activity=NULL"))
            elif inactive_days >= 90:
                candidates.append(("R01", "confirmed", f"La última actividad ocurrió hace {inactive_days} días", f"last_activity={last.isoformat()}"))
            if row["is_admin"] and not row["justification_verified"]:
                candidates.append(("R02", "confirmed", "La cuenta tiene rol administrativo sin justificación verificable", "is_admin=true; justification_verified=false"))
            if row["is_admin"] and row["is_duplicate"]:
                candidates.append(("R03", "potential", "El origen reporta una identidad administrativa potencialmente duplicada", "is_duplicate=true"))
            if row["account_type"] == "service" and row["password_never_expires"]:
                candidates.append(("R04", "confirmed", "La cuenta de servicio tiene password_never_expires habilitado", "account_type=service; password_never_expires=true"))
            roles = [x.strip() for x in str(row["privileged_roles"] or "").split("|") if x.strip()]
            out = [x for x in roles if x not in ALLOWED_PRIVILEGES]
            if out:
                candidates.append(("R05", "confirmed", f"Privilegios fuera de la política base: {', '.join(out)}", f"privileged_roles={row['privileged_roles']}"))
            review = row["review_at"]
            if score >= 60 and (review is None or (date.today() - review).days > 90):
                candidates.append(("R06", "potential", "El score es alto y no existe una revisión reciente", f"risk_score={score}; review_at={review or 'NULL'}"))
            for rule_id, state, rationale, evidence in candidates:
                exists = conn.execute(select(func.count()).select_from(findings).where(and_(findings.c.account_id == row["id"], findings.c.rule_id == rule_id, findings.c.status.not_in(["Resuelto", "Cerrado"])))) .scalar_one()
                if exists:
                    continue
                conn.execute(insert(findings).values(
                    account_id=row["id"], rule_id=rule_id, title=RULES[rule_id][0], severity=SEVERITY_BY_RULE[rule_id],
                    evidence_state=state, status="Detectado", rationale=rationale, evidence=evidence,
                    risk_score=score, owner=None, created_at=started, updated_at=started,
                ))
                created += 1
        conn.execute(update(runs).where(runs.c.id == run_id).values(status="completed", accounts_processed=len(account_rows), findings_created=created, finished_at=datetime.now(UTC)))
        audit_event(conn, actor, role, "run_detection", run_id, "success", f"Escaneo determinista completado: {len(account_rows)} cuentas, {created} hallazgos nuevos")
    return {"run_id": run_id, "accounts_processed": len(account_rows), "findings_created": created}


def account_frame() -> pd.DataFrame:
    return df(accounts, order_by=accounts.c.risk_score.desc())


def finding_frame() -> pd.DataFrame:
    stmt = select(
        findings.c.id, findings.c.rule_id, findings.c.title, findings.c.severity, findings.c.evidence_state,
        findings.c.status, findings.c.rationale, findings.c.evidence, findings.c.risk_score, findings.c.owner,
        findings.c.created_at, findings.c.updated_at, accounts.c.username, accounts.c.display_name,
        accounts.c.account_type, accounts.c.source,
    ).select_from(findings.join(accounts, findings.c.account_id == accounts.c.id)).order_by(findings.c.risk_score.desc(), findings.c.created_at.desc())
    with engine.connect() as conn:
        return pd.read_sql(stmt, conn)


def audit_frame() -> pd.DataFrame:
    return df(audit_logs, order_by=audit_logs.c.occurred_at.desc())


def run_frame() -> pd.DataFrame:
    return df(runs, order_by=runs.c.started_at.desc())


def update_finding(finding_id: int, status: str, owner: str | None, actor: str, role: str, comment: str = "") -> None:
    with engine.begin() as conn:
        current = conn.execute(select(findings).where(findings.c.id == finding_id)).mappings().first()
        if not current:
            raise ValueError("Hallazgo no encontrado")
        details = f"status={status}; owner={owner or 'sin asignar'}; comment={comment or 'sin comentario'}"
        conn.execute(update(findings).where(findings.c.id == finding_id).values(status=status, owner=owner or None, updated_at=datetime.now(UTC), rationale=(current["rationale"] + (f" | Comentario: {comment}" if comment else ""))[:5000]))
        audit_event(conn, actor, role, "update_finding", f"finding:{finding_id}", "success", details)


def dashboard_metrics() -> dict[str, Any]:
    a = account_frame()
    f = finding_frame()
    return {
        "accounts": len(a),
        "inactive": int(((pd.to_datetime(a["last_activity"]).isna()) | ((pd.to_datetime(a["last_activity"]) < pd.Timestamp(date.today() - timedelta(days=90))))).sum()),
        "orphans": int(((pd.to_datetime(a["last_activity"]).isna()) | ((pd.to_datetime(a["last_activity"]) < pd.Timestamp(date.today() - timedelta(days=90))))).sum()),
        "excessive": int((a["risk_score"] >= 60).sum()),
        "service_no_expiry": int(((a["account_type"] == "service") & (a["password_never_expires"] == True)).sum()),
        "open_findings": int((~f["status"].isin(["Resuelto", "Cerrado"])).sum()) if not f.empty else 0,
        "closed_findings": int(f["status"].isin(["Resuelto", "Cerrado"]).sum()) if not f.empty else 0,
        "risk_total": int(a["risk_score"].sum()),
    }


def api_health() -> dict[str, Any]:
    try:
        with engine.connect() as conn:
            conn.execute(select(func.count()).select_from(accounts)).scalar_one()
        return {"status": "ok", "database": "connected", "mode": "deterministic", "source": "synthetic demo"}
    except Exception as exc:
        return {"status": "degraded", "database": "error", "detail": str(exc)[:160]}


init_db()
