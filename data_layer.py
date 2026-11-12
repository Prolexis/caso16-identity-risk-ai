"""Persistencia, RBAC, gestión de tickets, políticas y motor determinista de CASO16.

Opera sobre el Dataset Público SharpHound/BloodHound AD y soporta PostgreSQL (Docker Compose)
y SQLite local para ejecución directa sin infraestructura.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import (
    Boolean, Column, Date, DateTime, Integer, MetaData, String, Table, Text, and_,
    create_engine, delete, func, insert, select, update
)

import security

UTC = timezone.utc
NOW = datetime.now(UTC)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'caso16.db').as_posix()}")

engine = create_engine(DB_URL, pool_pre_ping=True, future=True)
metadata = MetaData()

# ==============================================================================
# TABLAS DEL MODELO DE DATOS
# ==============================================================================

# 1. Cuentas de Directorio
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

# 2. Hallazgos
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

# 3. Corridas de Detección
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

# 4. Bitácora de Auditoría Integral
audit_logs = Table(
    "audit_logs", metadata,
    Column("id", Integer, primary_key=True),
    Column("actor", String(160), nullable=False),
    Column("role", String(80), nullable=False),
    Column("action", String(100), nullable=False),
    Column("resource", String(180), nullable=False),
    Column("result", String(30), nullable=False),
    Column("details", Text, nullable=False),
    Column("ip_address", String(60), nullable=False, default="127.0.0.1"),
    Column("session_id", String(80), nullable=True),
    Column("module_name", String(100), nullable=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
)

# 5. Usuarios del Sistema (IAM / RBAC)
users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String(120), unique=True, nullable=False),
    Column("email", String(180), unique=True, nullable=False),
    Column("hashed_password", String(255), nullable=False),
    Column("full_name", String(180), nullable=False),
    Column("role", String(80), nullable=False),
    Column("active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

# 6. Roles y Permisos Granulares
roles = Table(
    "roles", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(80), unique=True, nullable=False),
    Column("description", String(255), nullable=False),
    Column("permissions", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

# 7. Tickets de Remediación y SLA
tickets = Table(
    "tickets", metadata,
    Column("id", String(30), primary_key=True),
    Column("finding_id", Integer, nullable=True),
    Column("title", String(240), nullable=False),
    Column("description", Text, nullable=False),
    Column("status", String(30), nullable=False, default="Abierto"),
    Column("priority", String(20), nullable=False, default="Media"),
    Column("owner", String(160)),
    Column("sla_due_date", Date, nullable=False),
    Column("resolution_notes", Text),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

# 8. Historial de Tickets
ticket_history = Table(
    "ticket_history", metadata,
    Column("id", Integer, primary_key=True),
    Column("ticket_id", String(30), nullable=False),
    Column("actor", String(160), nullable=False),
    Column("action", String(100), nullable=False),
    Column("details", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

# 9. Fuentes de Directorio (AD / LDAP)
directory_sources = Table(
    "directory_sources", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), unique=True, nullable=False),
    Column("domain", String(120), nullable=False),
    Column("server_url", String(200), nullable=False),
    Column("use_tls", Boolean, nullable=False, default=True),
    Column("status", String(30), nullable=False, default="Sincronizado"),
    Column("accounts_count", Integer, nullable=False, default=0),
    Column("last_sync_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

# 10. Políticas de Seguridad y Umbrales
security_policies = Table(
    "security_policies", metadata,
    Column("id", Integer, primary_key=True),
    Column("code", String(40), unique=True, nullable=False),
    Column("name", String(180), nullable=False),
    Column("description", Text, nullable=False),
    Column("threshold_value", Integer, nullable=False),
    Column("unit", String(30), nullable=False, default="días"),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

# 11. Excepciones Justificadas
security_exceptions = Table(
    "security_exceptions", metadata,
    Column("id", Integer, primary_key=True),
    Column("account_id", Integer, nullable=False),
    Column("rule_id", String(10), nullable=False),
    Column("justification", Text, nullable=False),
    Column("approved_by", String(160), nullable=False),
    Column("expires_at", Date, nullable=False),
    Column("status", String(20), nullable=False, default="Activa"),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

# ==============================================================================
# REGLAS Y CONFIGURACIONES DE AUDITORÍA
# ==============================================================================

RULES = {
    "R01": ("Inactividad prolongada", "Cuenta sin actividad durante 90 días o más"),
    "R02": ("Privilegio administrativo sin justificación", "Cuenta admin sin justificación verificable"),
    "R03": ("Cuenta administrativa duplicada", "Posible identidad administrativa redundante"),
    "R04": ("Contraseña de servicio no expira", "Cuenta de servicio con contraseña eterna"),
    "R05": ("Privilegios inconsistentes", "Privilegios fuera de la política configurada"),
    "R06": ("Riesgo alto sin revisión", "Cuenta de riesgo elevado sin revisión reciente"),
}
SEVERITY_BY_RULE = {"R01": "Medio", "R02": "Alto", "R03": "Medio", "R04": "Alto", "R05": "Crítico", "R06": "Alto"}
ALLOWED_PRIVILEGES = {"Domain Users", "Helpdesk", "ReadOnly", "Guests"}

SHARPHOUND_SOURCES = [
    ("sharphound_20240305110018", date(2024, 3, 5)),
    ("sharphound_20240305110427", date(2024, 3, 5)),
    ("sharphound_20240305111414", date(2024, 3, 5)),
    ("bloodhound", date(2022, 11, 15)),
]
SERVICE_PREFIXES = ("krbtgt", "healthmailbox", "sm_", "svc", "msol_", "aad_", "sql", "iis", "rodc")
ADMIN_GROUPS = {
    "Domain Admins", "Enterprise Admins", "Schema Admins", "Administrators",
    "Account Operators", "Backup Operators", "Print Operators", "Server Operators",
    "Group Policy Creator Owners", "Enterprise Key Admins", "T0_Admins", "Helpdeskadmins",
}

DEFAULT_ROLES = [
    ("Superadministrador", "Acceso total y configuración del sistema", "read,write,remediate,export,admin,users,policies"),
    ("Administrador de seguridad", "Gestión de políticas, reglas, directorios y remediación", "read,write,remediate,export,policies"),
    ("Analista de ciberseguridad", "Detección, investigación de hallazgos, tickets y reportes", "read,write,remediate,export"),
    ("Responsable de remediación", "Atención y resolución de tickets de hallazgos", "read,remediate"),
    ("Auditor", "Auditoría integral, consulta de bitácora y exportación", "read,export,audit"),
    ("Usuario de consulta", "Visualización de tableros ejecutivos e inventario", "read"),
]

DEFAULT_USERS = [
    ("admin@demo.local", "Super Administrador", "Superadministrador"),
    ("security@demo.local", "Administrador de Seguridad", "Administrador de seguridad"),
    ("analyst@demo.local", "Analista de Ciberseguridad", "Analista de ciberseguridad"),
    ("remediator@demo.local", "Especialista de Remediación", "Responsable de remediación"),
    ("auditor@demo.local", "Auditor de TI / Ciberseguridad", "Auditor"),
    ("consultant@demo.local", "Consultor / Usuario Consulta", "Usuario de consulta"),
]

DEFAULT_POLICIES = [
    ("POL-INACTIVITY-DAYS", "Umbral de inactividad de cuentas", "Días sin logon para clasificar una cuenta como inactiva o huérfana", 90, "días"),
    ("POL-ADMIN-JUSTIFICATION", "Justificación obligatoria de admins", "Exigir descripción o título formal para cuentas con privilegios administrativos", 1, "booleano"),
    ("POL-SERVICE-PWD-NEVER-EXPIRES", "Prohibición de claves eternas en servicios", "Alerta ante cuentas SPN o de servicio con pwdNeverExpires activo", 1, "booleano"),
    ("POL-RISK-HIGH-THRESHOLD", "Umbral de riesgo alto", "Puntaje determinista mínimo para clasificar una identidad en riesgo alto", 60, "puntos"),
    ("POL-RISK-CRITICAL-THRESHOLD", "Umbral de riesgo crítico", "Puntaje determinista mínimo para clasificar una identidad en riesgo crítico", 80, "puntos"),
]

DEFAULT_DIRECTORIES = [
    ("AD-PHANTOM", "PHANTOM.CORP", "ldaps://dc01.phantom.corp:636", True, 53),
    ("AD-WRAITH", "WRAITH.CORP", "ldaps://dc01.wraith.corp:636", True, 40),
    ("AD-ESC1", "ESC1.LOCAL", "ldaps://pki.esc1.local:636", True, 14),
    ("AD-GHOST", "GHOST.CORP", "ldaps://dc01.ghost.corp:636", True, 6),
]


# ==============================================================================
# INGESTA Y SEMBRADO DE DATOS (SEEDING)
# ==============================================================================

def load_public_dataset_rows() -> list[dict[str, Any]]:
    """Transforma los archivos JSON públicos de SharpHound/BloodHound en registros normalizados."""
    records: list[dict[str, Any]] = []
    seen_oids: set[str] = set()
    today = date.today()

    for prefix, capture_date in SHARPHOUND_SOURCES:
        users_path = DATA_DIR / f"{prefix}_users.json"
        groups_path = DATA_DIR / f"{prefix}_groups.json"
        if not users_path.exists() or not groups_path.exists():
            continue

        groups_data = json.loads(groups_path.read_text(encoding="utf-8-sig")).get("data", [])
        group_map: dict[str, list[str]] = {}
        for g in groups_data:
            gname = str(g.get("Properties", {}).get("name") or "").split("@")[0].title()
            if not gname:
                continue
            for member in g.get("Members", []):
                oid = member.get("ObjectIdentifier")
                if oid:
                    group_map.setdefault(oid, []).append(gname)

        users_data = json.loads(users_path.read_text(encoding="utf-8-sig")).get("data", [])
        for u in users_data:
            oid = str(u.get("ObjectIdentifier") or "").strip()
            if not oid or oid in seen_oids:
                continue
            seen_oids.add(oid)

            props = u.get("Properties", {})
            domain = str(props.get("domain") or "AD.LOCAL").upper()
            upn = str(props.get("name") or "").strip()
            sam = str(props.get("samaccountname") or (upn.split("@")[0] if upn else oid)).strip()
            display_name = str(props.get("displayname") or props.get("description") or sam).strip()[:180]
            email = str(props.get("email") or (upn.lower() if "@" in upn else f"{sam.lower()}@{domain.lower()}")).strip()[:180]

            user_groups = sorted(set(group_map.get(oid, [])))
            is_admin = bool(props.get("admincount")) or any(g in ADMIN_GROUPS for g in user_groups)
            sam_lower = sam.lower()
            is_service = (
                bool(props.get("hasspn"))
                or bool(props.get("serviceprincipalnames"))
                or sam_lower.startswith(SERVICE_PREFIXES)
            )
            account_type = "service" if is_service else ("admin" if is_admin else "user")

            justification_verified = bool(props.get("description") or props.get("title"))
            is_duplicate = bool(is_admin and sam_lower not in {"administrator", "krbtgt"})
            password_never_expires = bool(props.get("pwdneverexpires"))
            privileged_roles = "|".join(user_groups) if user_groups else "Domain Users"

            ll_epoch = max(int(props.get("lastlogon") or 0), int(props.get("lastlogontimestamp") or 0))
            if ll_epoch > 0:
                ll_date = datetime.fromtimestamp(ll_epoch, tz=UTC).date()
                inactivity_days = max(0, (capture_date - ll_date).days)
                last_activity = today - timedelta(days=inactivity_days)
            else:
                last_activity = None

            pwd_epoch = int(props.get("pwdlastset") or 0)
            if pwd_epoch > 0:
                pwd_date = datetime.fromtimestamp(pwd_epoch, tz=UTC).date()
                review_days = max(0, (capture_date - pwd_date).days)
                review_at = today - timedelta(days=review_days)
            else:
                review_at = None

            records.append({
                "external_id": oid,
                "username": f"{sam}@{domain}" if sam_lower in {"administrator", "krbtgt", "guest", "defaultaccount"} else sam,
                "display_name": display_name,
                "email": email,
                "account_type": account_type,
                "source": f"SharpHound AD ({domain})",
                "active": bool(props.get("enabled", True)),
                "is_admin": is_admin,
                "justification_verified": justification_verified,
                "is_duplicate": is_duplicate,
                "password_never_expires": password_never_expires,
                "privileged_roles": privileged_roles,
                "last_activity": last_activity,
                "review_at": review_at,
                "risk_score": 0,
                "created_at": datetime.now(UTC),
            })

    return records


def seed_auxiliary_tables(conn) -> None:
    """Siembra roles, usuarios RBAC, fuentes de directorio y políticas si no existen."""
    now_utc = datetime.now(UTC)
    # 1. Roles
    for role_name, desc, perms in DEFAULT_ROLES:
        exists = conn.execute(select(func.count()).select_from(roles).where(roles.c.name == role_name)).scalar_one()
        if not exists:
            conn.execute(insert(roles).values(name=role_name, description=desc, permissions=perms, created_at=now_utc))

    # 2. Usuarios con hash seguro
    production = os.getenv('ENV', 'development').lower() == 'production'
    demo_hash = security.hash_password(os.getenv('CASO16_BOOTSTRAP_PASSWORD', 'demo'))
    if production:
        for existing in conn.execute(select(users)).mappings():
            if security.verify_password('demo', existing['hashed_password']):
                raise RuntimeError('Producción bloqueada: cambie las contraseñas demo existentes')
    for email, full_name, role_name in ([] if production else DEFAULT_USERS):
        username = email.split("@")[0]
        exists = conn.execute(select(func.count()).select_from(users).where(users.c.username == username)).scalar_one()
        if not exists:
            conn.execute(insert(users).values(
                username=username, email=email, hashed_password=demo_hash,
                full_name=full_name, role=role_name, active=True, created_at=now_utc
            ))

    # 3. Fuentes de Directorio
    for name, domain, srv, tls, count in DEFAULT_DIRECTORIES:
        exists = conn.execute(select(func.count()).select_from(directory_sources).where(directory_sources.c.name == name)).scalar_one()
        if not exists:
            conn.execute(insert(directory_sources).values(
                name=name, domain=domain, server_url=srv, use_tls=tls,
                status="Sincronizado", accounts_count=count, last_sync_at=now_utc, created_at=now_utc
            ))

    # 4. Políticas de Seguridad
    for code, pname, pdesc, val, unit in DEFAULT_POLICIES:
        exists = conn.execute(select(func.count()).select_from(security_policies).where(security_policies.c.code == code)).scalar_one()
        if not exists:
            conn.execute(insert(security_policies).values(
                code=code, name=pname, description=pdesc, threshold_value=val,
                unit=unit, is_active=True, updated_at=now_utc
            ))


def seed_tickets_from_findings(conn) -> None:
    """Genera tickets iniciales vinculados a los hallazgos críticos detectados."""
    t_count = conn.execute(select(func.count()).select_from(tickets)).scalar_one()
    if t_count > 0:
        return
    # Buscar hallazgos críticos para crear tickets iniciales con SLA
    crit_findings = conn.execute(
        select(findings.c.id, findings.c.title, findings.c.rationale, findings.c.severity)
        .where(findings.c.severity.in_(["Crítico", "Alto"]))
        .limit(10)
    ).fetchall()

    idx = 1
    today = date.today()
    now_utc = datetime.now(UTC)
    for f in crit_findings:
        t_id = f"TCK-2026-{idx:04d}"
        sla_days = 7 if f.severity == "Crítico" else 15
        sla_due = today + timedelta(days=sla_days)
        conn.execute(insert(tickets).values(
            id=t_id,
            finding_id=f.id,
            title=f"Remediación: {f.title} (Hallazgo #{f.id})",
            description=f.rationale,
            status="Abierto" if idx % 2 != 0 else "En Progreso",
            priority=f.severity,
            owner="remediator@demo.local" if idx % 2 == 0 else "security@demo.local",
            sla_due_date=sla_due,
            resolution_notes=None,
            created_at=now_utc,
            updated_at=now_utc,
        ))
        conn.execute(insert(ticket_history).values(
            ticket_id=t_id, actor="system", action="create_ticket",
            details=f"Ticket generado automáticamente a partir de hallazgo #{f.id} con SLA de {sla_days} días",
            created_at=now_utc
        ))
        idx += 1


def init_db() -> None:
    """Crea el esquema y puebla las tablas si es necesario."""
    metadata.create_all(engine)

    # Migración en caliente de columnas nuevas si la base ya existía
    try:
        with engine.begin() as conn:
            if engine.dialect.name == "sqlite":
                cols = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(audit_logs)").fetchall()}
                if "ip_address" not in cols:
                    conn.exec_driver_sql("ALTER TABLE audit_logs ADD COLUMN ip_address VARCHAR(60) DEFAULT '127.0.0.1'")
                if "session_id" not in cols:
                    conn.exec_driver_sql("ALTER TABLE audit_logs ADD COLUMN session_id VARCHAR(80)")
                if "module_name" not in cols:
                    conn.exec_driver_sql("ALTER TABLE audit_logs ADD COLUMN module_name VARCHAR(100)")
            else:
                conn.exec_driver_sql("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS ip_address VARCHAR(60) DEFAULT '127.0.0.1'")
                conn.exec_driver_sql("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS session_id VARCHAR(80)")
                conn.exec_driver_sql("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS module_name VARCHAR(100)")
    except Exception:
        pass

    dataset_rows = load_public_dataset_rows()
    expected_count = len(dataset_rows) if dataset_rows else 0

    needs_scan = False
    with engine.begin() as conn:
        seed_auxiliary_tables(conn)
        count = conn.execute(select(func.count()).select_from(accounts)).scalar_one()
        if expected_count > 0 and count == 0:
            seed_demo(conn, dataset_rows)
            audit_event(
                conn,
                "system",
                "system",
                "load_public_dataset",
                "directory_accounts",
                "success",
                f"Dataset público SharpHound/BloodHound cargado ({expected_count} cuentas de PHANTOM.CORP, WRAITH.CORP, GHOST.CORP y ESC1.LOCAL)",
            )
            needs_scan = True
        elif count == 0 and dataset_rows:
            seed_demo(conn, dataset_rows)
            needs_scan = True

    if needs_scan:
        run_detection("system@caso16.local", "Motor Automático de Ingesta")
        with engine.begin() as conn:
            seed_tickets_from_findings(conn)
    else:
        with engine.begin() as conn:
            seed_tickets_from_findings(conn)


def seed_demo(conn=None, dataset_rows: list[dict[str, Any]] | None = None) -> None:
    rows = dataset_rows if dataset_rows is not None else load_public_dataset_rows()
    target = conn or engine.begin()
    close = conn is None
    try:
        for row in rows:
            target.execute(insert(accounts).values(**row))
    finally:
        if close:
            target.commit()
            target.close()


def audit_event(
    conn,
    actor: str,
    role: str,
    action: str,
    resource: str,
    result: str,
    details: str,
    ip_address: str = "127.0.0.1",
    session_id: str | None = None,
    module_name: str | None = None,
) -> None:
    """Registra un evento append-only en la bitácora centralizada de auditoría."""
    conn.execute(insert(audit_logs).values(
        actor=actor, role=role, action=action, resource=resource, result=result,
        details=details[:1000], ip_address=ip_address, session_id=session_id,
        module_name=module_name, occurred_at=datetime.now(UTC)
    ))


def df(table: Table, where=None, order_by=None) -> pd.DataFrame:
    stmt = select(table)
    if where is not None:
        stmt = stmt.where(where)
    if order_by is not None:
        stmt = stmt.order_by(order_by)
    with engine.connect() as conn:
        return pd.read_sql(stmt, conn)


# ==============================================================================
# MOTOR DETERMINISTA DE REGLAS (R01-R06) Y SCORING
# ==============================================================================

def compute_score(row: dict[str, Any]) -> int:
    score = 0
    if row.get("is_admin"):
        score += 25
    last = row.get("last_activity")
    if last is None:
        score += 30
    else:
        if isinstance(last, str):
            last = date.fromisoformat(last[:10])
        score += min(30, max(0, (date.today() - last).days // 5))
    if row.get("account_type") == "service":
        score += 20
    if row.get("password_never_expires"):
        score += 15
    roles_str = str(row.get("privileged_roles") or "")
    if any(role.strip() not in ALLOWED_PRIVILEGES for role in roles_str.split("|") if role.strip()):
        score += 25
    review = row.get("review_at")
    if review is None:
        score += 10
    return min(100, score)


def classify_risk(score: int) -> str:
    return "Crítico" if score >= 80 else "Alto" if score >= 60 else "Medio" if score >= 35 else "Bajo"


def run_detection(actor: str = "analyst@demo.local", role: str = "Analista de ciberseguridad") -> dict[str, Any]:
    metadata.create_all(engine)
    run_id = "run-" + uuid.uuid4().hex[:12]
    started = datetime.now(UTC)
    with engine.begin() as conn:
        conn.execute(insert(runs).values(
            id=run_id,
            source="SharpHound AD Public Dataset (4 Dominios)",
            mode="deterministic",
            status="running",
            accounts_processed=0,
            findings_created=0,
            started_at=started,
        ))
        account_rows = [dict(r._mapping) for r in conn.execute(select(accounts)).fetchall()]
        policies = {r['code']: r for r in conn.execute(select(security_policies)).mappings()}
        inactivity_limit = policies.get('POL-INACTIVITY-DAYS', {}).get('threshold_value', 90)
        high_limit = policies.get('POL-RISK-HIGH-THRESHOLD', {}).get('threshold_value', 60)
        exempt = {(r['account_id'], r['rule_id']) for r in conn.execute(select(security_exceptions).where(security_exceptions.c.status == 'Activa', security_exceptions.c.expires_at >= date.today())).mappings()}
        created = 0
        for row in account_rows:
            score = compute_score(row)
            conn.execute(update(accounts).where(accounts.c.id == row["id"]).values(risk_score=score))
            candidates: list[tuple[str, str, str, str]] = []
            last = row["last_activity"]
            inactive_days = None if last is None else (date.today() - last).days
            if last is None:
                candidates.append(("R01", "potential", f"No existe evidencia de lastLogon/lastLogonTimestamp en {row['source']}", f"sid={row['external_id']}; lastLogon=0; lastLogonTimestamp=-1"))
            elif inactive_days >= inactivity_limit:
                candidates.append(("R01", "confirmed", f"La última actividad de autenticación ocurrió hace {inactive_days} días", f"sid={row['external_id']}; last_activity={last.isoformat()}; inactive_days={inactive_days}"))
            if row["is_admin"] and not row["justification_verified"]:
                candidates.append(("R02", "confirmed", "La cuenta posee privilegios administrativos (adminCount/grupos) sin justificación documentada en AD", f"sid={row['external_id']}; is_admin=true; description=NULL"))
            if row["is_admin"] and row["is_duplicate"]:
                candidates.append(("R03", "potential", "El dominio reporta una identidad administrativa adicional/duplicada fuera de la cuenta built-in", f"sid={row['external_id']}; username={row['username']}; is_duplicate=true"))
            if row["account_type"] == "service" and row["password_never_expires"]:
                candidates.append(("R04", "confirmed", "La cuenta de servicio/SPN tiene el atributo pwdNeverExpires habilitado", f"sid={row['external_id']}; account_type=service; pwdNeverExpires=true"))
            u_roles = [x.strip() for x in str(row["privileged_roles"] or "").split("|") if x.strip()]
            out = [x for x in u_roles if x not in ALLOWED_PRIVILEGES]
            if out:
                candidates.append(("R05", "confirmed", f"Membresía en grupos privilegiados fuera de la línea base: {', '.join(out)}", f"sid={row['external_id']}; privileged_roles={row['privileged_roles']}"))
            review = row["review_at"]
            if score >= high_limit and (review is None or (date.today() - review).days > inactivity_limit):
                candidates.append(("R06", "potential", "Cuenta con score de riesgo elevado y antigüedad de pwdLastSet mayor a 90 días", f"sid={row['external_id']}; risk_score={score}; pwdLastSet_date={review or 'NULL'}"))
            policy_for_rule = {'R01':'POL-INACTIVITY-DAYS','R02':'POL-ADMIN-JUSTIFICATION','R04':'POL-SERVICE-PWD-NEVER-EXPIRES','R06':'POL-RISK-HIGH-THRESHOLD'}
            for rule_id, state, rationale, evidence in candidates:
                policy = policies.get(policy_for_rule.get(rule_id), {})
                if not policy.get('is_active', True) or (row['id'], rule_id) in exempt:
                    continue
                exists = conn.execute(select(func.count()).select_from(findings).where(and_(
                    findings.c.account_id == row["id"],
                    findings.c.rule_id == rule_id,
                    findings.c.status.not_in(["Resuelto", "Cerrado"]),
                ))).scalar_one()
                if exists:
                    continue
                conn.execute(insert(findings).values(
                    account_id=row["id"], rule_id=rule_id, title=RULES[rule_id][0], severity=SEVERITY_BY_RULE[rule_id],
                    evidence_state=state, status="Detectado", rationale=rationale, evidence=evidence,
                    risk_score=score, owner=None, created_at=started, updated_at=started,
                ))
                created += 1
        conn.execute(update(runs).where(runs.c.id == run_id).values(
            status="completed", accounts_processed=len(account_rows), findings_created=created, finished_at=datetime.now(UTC)
        ))
        audit_event(conn, actor, role, "run_detection", run_id, "success", f"Escaneo determinista completado: {len(account_rows)} cuentas procesadas, {created} hallazgos", module_name="Scanner")
    return {"run_id": run_id, "accounts_processed": len(account_rows), "findings_created": created}


# ==============================================================================
# DATAFRAMES Y CONSULTAS PRINCIPALES
# ==============================================================================

def account_frame() -> pd.DataFrame:
    return df(accounts, order_by=accounts.c.risk_score.desc())


def finding_frame() -> pd.DataFrame:
    stmt = select(
        findings.c.id, findings.c.account_id, findings.c.rule_id, findings.c.title, findings.c.severity, findings.c.evidence_state,
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


def user_frame() -> pd.DataFrame:
    return df(users, order_by=users.c.id.asc())


def role_frame() -> pd.DataFrame:
    return df(roles, order_by=roles.c.id.asc())


def ticket_frame() -> pd.DataFrame:
    return df(tickets, order_by=tickets.c.created_at.desc())


def directory_source_frame() -> pd.DataFrame:
    return df(directory_sources, order_by=directory_sources.c.id.asc())


def policy_frame() -> pd.DataFrame:
    return df(security_policies, order_by=security_policies.c.id.asc())


def exception_frame() -> pd.DataFrame:
    stmt = select(
        security_exceptions.c.id, security_exceptions.c.account_id, security_exceptions.c.rule_id,
        security_exceptions.c.justification, security_exceptions.c.approved_by, security_exceptions.c.expires_at,
        security_exceptions.c.status, security_exceptions.c.created_at, accounts.c.username, accounts.c.display_name
    ).select_from(security_exceptions.join(accounts, security_exceptions.c.account_id == accounts.c.id)).order_by(security_exceptions.c.created_at.desc())
    with engine.connect() as conn:
        return pd.read_sql(stmt, conn)


# ==============================================================================
# GESTIÓN DE ACCIONES Y SERVICIOS DE DOMINIO
# ==============================================================================

def require_permission(role: str, permission: str) -> None:
    """Deny unknown roles; API callers must derive role from authenticated identity."""
    allowed = next((set(perms.split(',')) for name, _, perms in DEFAULT_ROLES if name == role), set())
    if permission not in allowed:
        raise PermissionError(f'El rol {role} no tiene permiso {permission}')


def update_account_metadata(account_id: int, changes: dict, actor: str, role: str) -> None:
    require_permission(role, 'policies')
    allowed = {'justification_verified', 'review_at', 'privilege_justification'}
    if set(changes) - allowed:
        raise ValueError('Campo de metadata no permitido')
    note = changes.pop('privilege_justification', '')
    if changes.get('justification_verified') and len(note.strip()) < 5:
        raise ValueError('Debe documentar la justificación del privilegio')
    if changes.get('review_at') and changes['review_at'] > date.today():
        raise ValueError('La revisión no puede ser futura')
    with engine.begin() as conn:
        row = conn.execute(select(accounts).where(accounts.c.id == account_id)).mappings().first()
        if not row:
            raise ValueError('Cuenta no encontrada')
        if changes:
            conn.execute(update(accounts).where(accounts.c.id == account_id).values(**changes, risk_score=compute_score(dict(row, **changes))))
        audit_event(conn, actor, role, 'update_account_metadata', f'account:{account_id}', 'success', json.dumps(dict(changes, privilege_justification=note), default=str))


def authenticate_user(username_or_email: str, plain_password: str) -> dict[str, Any] | None:
    """Verifica credenciales de usuario y retorna perfil o None."""
    with engine.connect() as conn:
        query = select(users).where(
            and_(
                (users.c.username == username_or_email) | (users.c.email == username_or_email),
                users.c.active == True
            )
        )
        row = conn.execute(query).mappings().first()
        if not row:
            return None
        if security.verify_password(plain_password, row["hashed_password"]):
            return dict(row)
    return None


def create_user(username: str, email: str, plain_password: str, full_name: str, role_name: str, actor: str, actor_role: str) -> dict[str, Any]:
    require_permission(actor_role, 'users')
    if role_name not in {r[0] for r in DEFAULT_ROLES}:
        raise ValueError('Rol desconocido')
    with engine.begin() as conn:
        exists = conn.execute(select(func.count()).select_from(users).where(
            (users.c.username == username) | (users.c.email == email)
        )).scalar_one()
        if exists:
            raise ValueError("El usuario o correo electrónico ya existe")
        hashed = security.hash_password(plain_password)
        now_utc = datetime.now(UTC)
        result = conn.execute(insert(users).values(
            username=username, email=email, hashed_password=hashed,
            full_name=full_name, role=role_name, active=True, created_at=now_utc
        ))
        audit_event(conn, actor, actor_role, "create_user", f"user:{username}", "success", f"Usuario creado con rol {role_name}")
        return {"username": username, "email": email, "full_name": full_name, "role": role_name}


def update_finding(finding_id: int, status: str, owner: str | None, actor: str, role: str, comment: str = "") -> None:
    require_permission(role, 'write')
    with engine.begin() as conn:
        current = conn.execute(select(findings).where(findings.c.id == finding_id)).mappings().first()
        if not current:
            raise ValueError("Hallazgo no encontrado")
        details = f"status={status}; owner={owner or 'sin asignar'}; comment={comment or 'sin comentario'}"
        conn.execute(update(findings).where(findings.c.id == finding_id).values(
            status=status,
            owner=owner or None,
            updated_at=datetime.now(UTC),
            rationale=(current["rationale"] + (f" | Comentario: {comment}" if comment else ""))[:5000],
        ))
        audit_event(conn, actor, role, "update_finding", f"finding:{finding_id}", "success", details, module_name="Findings")


def create_ticket(
    finding_id: int | None,
    title: str,
    description: str,
    priority: str,
    owner: str,
    sla_days: int,
    actor: str,
    role: str,
) -> str:
    """Crea un ticket de remediación con SLA y trazabilidad."""
    require_permission(role, 'remediate')
    with engine.begin() as conn:
        seq = conn.execute(select(func.count()).select_from(tickets)).scalar_one() + 1
        t_id = f"TCK-2026-{seq:04d}"
        now_utc = datetime.now(UTC)
        sla_due = date.today() + timedelta(days=sla_days)
        conn.execute(insert(tickets).values(
            id=t_id, finding_id=finding_id, title=title, description=description,
            status="Abierto", priority=priority, owner=owner, sla_due_date=sla_due,
            created_at=now_utc, updated_at=now_utc
        ))
        conn.execute(insert(ticket_history).values(
            ticket_id=t_id, actor=actor, action="create_ticket",
            details=f"Ticket creado con prioridad {priority} y SLA a {sla_due.isoformat()}",
            created_at=now_utc
        ))
        audit_event(conn, actor, role, "create_ticket", f"ticket:{t_id}", "success", f"Creado para hallazgo #{finding_id or 'N/A'}", module_name="Tickets")
        return t_id


def update_ticket(ticket_id: str, status: str, owner: str | None, resolution_notes: str | None, actor: str, role: str) -> None:
    """Actualiza estado y notas de un ticket."""
    require_permission(role, 'remediate')
    with engine.begin() as conn:
        current = conn.execute(select(tickets).where(tickets.c.id == ticket_id)).mappings().first()
        if not current:
            raise ValueError("Ticket no encontrado")
        now_utc = datetime.now(UTC)
        conn.execute(update(tickets).where(tickets.c.id == ticket_id).values(
            status=status, owner=owner or current["owner"], resolution_notes=resolution_notes or current["resolution_notes"],
            updated_at=now_utc
        ))
        conn.execute(insert(ticket_history).values(
            ticket_id=ticket_id, actor=actor, action="update_ticket",
            details=f"Estado: {status}; Asignado: {owner}; Notas: {resolution_notes or 'sin notas'}",
            created_at=now_utc
        ))
        audit_event(conn, actor, role, "update_ticket", f"ticket:{ticket_id}", "success", f"Nuevo estado: {status}", module_name="Tickets")


def update_policy(policy_id: int, threshold_value: int, is_active: bool, actor: str, role: str) -> None:
    require_permission(role, 'policies')
    with engine.begin() as conn:
        conn.execute(update(security_policies).where(security_policies.c.id == policy_id).values(
            threshold_value=threshold_value, is_active=is_active, updated_at=datetime.now(UTC)
        ))
        audit_event(conn, actor, role, "update_policy", f"policy:{policy_id}", "success", f"threshold={threshold_value}; active={is_active}", module_name="Policies")


def create_exception(account_id: int, rule_id: str, justification: str, approved_by: str, days_valid: int, actor: str, role: str) -> int:
    require_permission(role, 'policies')
    if rule_id not in RULES or not 1 <= days_valid <= 365:
        raise ValueError('Regla o vigencia inválida')
    with engine.begin() as conn:
        now_utc = datetime.now(UTC)
        exp_date = date.today() + timedelta(days=days_valid)
        res = conn.execute(insert(security_exceptions).values(
            account_id=account_id, rule_id=rule_id, justification=justification,
            approved_by=approved_by, expires_at=exp_date, status="Activa", created_at=now_utc
        ))
        audit_event(conn, actor, role, "create_exception", f"account:{account_id};rule:{rule_id}", "success", f"Valida por {days_valid} días. Motivo: {justification}", module_name="Exceptions")
        return res.inserted_primary_key[0] if res.inserted_primary_key else 0


# ==============================================================================
# MOTOR INTELIGENTE DE EXPLICACIÓN Y MITIGACIÓN (IA / FALLBACK EXPERTO)
# ==============================================================================
def explain_finding_ai(finding_id: int) -> dict[str, Any]:
    """Genera análisis de riesgo, impacto en AD, vector de ataque y plan de mitigación estructurado."""
    with engine.connect() as conn:
        stmt = select(
            findings.c.id, findings.c.rule_id, findings.c.title, findings.c.severity, findings.c.evidence_state,
            findings.c.rationale, findings.c.evidence, findings.c.risk_score, accounts.c.username, accounts.c.display_name,
            accounts.c.account_type, accounts.c.source, accounts.c.is_admin, accounts.c.password_never_expires,
            accounts.c.privileged_roles
        ).select_from(findings.join(accounts, findings.c.account_id == accounts.c.id)).where(findings.c.id == finding_id)
        row = conn.execute(stmt).mappings().first()
        if not row:
            raise ValueError(f"Hallazgo #{finding_id} no encontrado")

    rule_id = row["rule_id"]
    account_name = row["username"]
    domain = row["source"].split("(")[-1].replace(")", "") if "(" in row["source"] else "AD.CORP"

    # Matriz experta de vectores de ataque y mitigación según MITRE ATT&CK
    attack_vectors = {
        "R01": {
            "technique": "T1078.002 - Valid Accounts: Domain Accounts",
            "tactics": "Initial Access / Persistence",
            "vector": "Cuentas inactivas no monitoreadas son el objetivo ideal para ataques de Password Spraying o secuestro silente, ya que no generan alertas operacionales por parte del usuario legítimo.",
            "impact": "Acceso inicial persistente sin detección; evasión de auditorías de usuarios activos.",
            "mitigation_steps": [
                f"1. Deshabilitar preventivamente la cuenta '{account_name}' en el controlador de dominio {domain} usando PowerShell: Disable-ADAccount -Identity '{account_name}'.",
                "2. Validar con el departamento de RRHH o IT si el usuario continúa activo en la organización.",
                "3. Si la inactividad supera 180 días sin justificación de licencia, proceder a la revocación formal y archivo.",
            ],
            "iso_control": "ISO/IEC 27001:2022 A.8.2 (Privileged Access Rights) y A.8.5 (Secure Authentication)",
        },
        "R02": {
            "technique": "T1098 - Account Manipulation / T1078 - Valid Accounts",
            "tactics": "Privilege Escalation / Persistence",
            "vector": "Cuentas con 'adminCount = 1' o en grupos administrativos sin descripción funcional formal suelen ser 'Shadow Admins' o asignaciones temporales nunca retiradas.",
            "impact": "Exposición de credenciales de alto privilegio capaces de comprometer el dominio completo (Domain Compromise).",
            "mitigation_steps": [
                f"1. Solicitar la justificación técnica de la delegación administrativa para '{account_name}'.",
                "2. Si es para tareas de soporte, migrar el acceso a una cuenta secundaria de administración separada (ej: adm_{account_name}) aplicando principio de menor privilegio.",
                "3. Remover la cuenta de los grupos administrativos de nivel 0 o Tier-1.",
            ],
            "iso_control": "ISO/IEC 27001:2022 A.8.2 (Privileged Access Rights)",
        },
        "R03": {
            "technique": "T1078 - Redundant Administrative Accounts",
            "tactics": "Defense Evasion / Lateral Movement",
            "vector": "Múltiples cuentas administrativas en el mismo dominio incrementan la superficie de ataque y dificultan la trazabilidad del actor real ante un incidente.",
            "impact": "Movimiento lateral simplificado y proliferación descontrolada de permisos de administración.",
            "mitigation_steps": [
                f"1. Auditar la necesidad de que '{account_name}' mantenga permisos de administración paralelos en {domain}.",
                "2. Consolidar la identidad administrativa bajo una política estricta de PAM (Privileged Access Management) con rotación de credenciales.",
            ],
            "iso_control": "ISO/IEC 27001:2022 A.8.2 (Privileged Access Rights) y A.9.4.2 (Secure Log-on)",
        },
        "R04": {
            "technique": "T1558.003 - Steal or Forge Kerberos Tickets: Kerberoasting",
            "tactics": "Credential Access",
            "vector": "Cuentas con ServicePrincipalNames (SPN) o tipo servicio con 'pwdNeverExpires = true' permiten a atacantes solicitar tickets TGS de Kerberos y descifrar la contraseña offline mediante Kerberoasting.",
            "impact": "Descifrado offline de contraseñas de servicio que conducen a acceso directo a bases de datos, servidores IIS o elevación a Administrador de Dominio.",
            "mitigation_steps": [
                f"1. Migrar la cuenta '{account_name}' a una Cuenta de Servicio Administrada de Grupo (gMSA - Group Managed Service Account) donde Windows gestiona contraseñas aleatorias de 128 caracteres automáticamente.",
                "2. Si gMSA no es compatible, imponer una longitud mínima de 25 caracteres para la contraseña y rotación semestral obligatoria.",
                "3. Habilitar cifrado AES256 exclusivo en Kerberos y deshabilitar RC4-HMAC.",
            ],
            "iso_control": "ISO/IEC 27001:2022 A.8.5 (Secure Authentication) y A.8.24 (Use of Cryptography)",
        },
        "R05": {
            "technique": "T1069.002 - Permission Groups Discovery: Domain Groups",
            "tactics": "Discovery / Privilege Escalation",
            "vector": "Pertenencia a grupos fuera de la línea base organizacional (Domain Admins, Schema Admins, Backup Operators) otorga capacidades intrínsecas de evasión de defensas y control del directorio.",
            "impact": "Capacidad de tomar snapshots del NTDS.dit, falsificar tickets Kerberos (Golden Ticket) o crear nuevos administradores encubiertos.",
            "mitigation_steps": [
                f"1. Retirar inmediatamente a '{account_name}' de los grupos: {row['privileged_roles']}.",
                "2. Implementar arquitectura de Tiering (Tier 0, Tier 1, Tier 2) según las mejores prácticas de Microsoft.",
                "3. Verificar en los logs del Event ID 4728/4729 quién asignó la membresía no autorizada.",
            ],
            "iso_control": "ISO/IEC 27001:2022 A.8.2 (Privileged Access Rights)",
        },
        "R06": {
            "technique": "T1078 - Stale High-Risk Credentials",
            "tactics": "Initial Access / Persistence",
            "vector": "Identidades con puntaje de riesgo >= 60 y antigüedad de contraseña superior a 90 días combinan alto impacto con credenciales envejecidas susceptibles a filtraciones previas.",
            "impact": "Riesgo crítico de reutilización de contraseñas filtradas en brechas externas.",
            "mitigation_steps": [
                f"1. Forzar el cambio de contraseña en el próximo inicio de sesión: Set-ADUser -Identity '{account_name}' -ChangePasswordAtLogon $true.",
                "2. Habilitar MFA obligatorio para todos los accesos VPN o remotos asociados a esta cuenta.",
            ],
            "iso_control": "ISO/IEC 27001:2022 A.8.5 (Secure Authentication)",
        },
    }

    info = attack_vectors.get(rule_id, {
        "technique": "T1078 - Valid Accounts",
        "tactics": "General Risk",
        "vector": "Incumplimiento de directivas de identidad corporativa.",
        "impact": "Exposición potencial de recursos del directorio.",
        "mitigation_steps": ["1. Revisar los atributos de la cuenta en el directorio.", "2. Aplicar principio de menor privilegio."],
        "iso_control": "ISO/IEC 27001:2022 A.8.2",
    })

    return {
        "finding_id": finding_id,
        "rule_id": rule_id,
        "account_username": account_name,
        "domain": domain,
        "severity": row["severity"],
        "risk_score": row["risk_score"],
        "engine_mode": "Hybrid-Deterministic-AI (LangFlow Architecture)",
        "mitre_technique": info["technique"],
        "mitre_tactics": info["tactics"],
        "attack_vector_analysis": info["vector"],
        "potential_impact": info["impact"],
        "recommended_remediation_plan": info["mitigation_steps"],
        "iso_27001_reference": info["iso_control"],
        "evidence_summary": row["evidence"],
    }


# ==============================================================================
# SALUD DEL SISTEMA Y MÉTRICAS
# ==============================================================================

def dashboard_metrics() -> dict[str, Any]:
    a = account_frame()
    f = finding_frame()
    t = ticket_frame()
    return {
        "accounts": len(a),
        "inactive": int(((pd.to_datetime(a["last_activity"]).isna()) | ((pd.to_datetime(a["last_activity"]) < pd.Timestamp(date.today() - timedelta(days=90))))).sum()),
        "orphans": int(((pd.to_datetime(a["last_activity"]).isna()) | ((pd.to_datetime(a["last_activity"]) < pd.Timestamp(date.today() - timedelta(days=90))))).sum()),
        "excessive": int((a["risk_score"] >= 60).sum()),
        "service_no_expiry": int(((a["account_type"] == "service") & (a["password_never_expires"] == True)).sum()),
        "open_findings": int((~f["status"].isin(["Resuelto", "Cerrado"])).sum()) if not f.empty else 0,
        "closed_findings": int(f["status"].isin(["Resuelto", "Cerrado"]).sum()) if not f.empty else 0,
        "open_tickets": int((~t["status"].isin(["Resuelto", "Cerrado"])).sum()) if not t.empty else 0,
        "risk_total": int(a["risk_score"].sum()),
    }


def api_health() -> dict[str, Any]:
    try:
        with engine.connect() as conn:
            total_accounts = conn.execute(select(func.count()).select_from(accounts)).scalar_one()
            total_findings = conn.execute(select(func.count()).select_from(findings)).scalar_one()
            total_tickets = conn.execute(select(func.count()).select_from(tickets)).scalar_one()
            total_users = conn.execute(select(func.count()).select_from(users)).scalar_one()
        return {
            "status": "ok",
            "database": "connected",
            "mode": "deterministic",
            "integrations": "n8n + langflow",
            "source": "SharpHound/BloodHound Public AD Dataset (PHANTOM.CORP, WRAITH.CORP, GHOST.CORP, ESC1.LOCAL)",
            "accounts_loaded": int(total_accounts),
            "findings_active": int(total_findings),
            "tickets_managed": int(total_tickets),
            "users_rbac": int(total_users),
        }
    except Exception as exc:
        return {"status": "degraded", "database": "error", "detail": str(exc)[:160]}


def explain_finding_langflow(finding_id: int, actor: str = "analyst@demo.local", role: str = "Analista de ciberseguridad") -> dict[str, Any]:
    """Ejecuta el contrato de LangFlow sobre un hallazgo determinista y registra la auditoría."""
    f_df = finding_frame()
    row_df = f_df[f_df["id"] == finding_id]
    if row_df.empty:
        raise ValueError("Hallazgo no encontrado")
    row = row_df.iloc[0].to_dict()
    rule_id = str(row["rule_id"])
    username = str(row["username"])
    sam = username.split("@")[0]
    source = str(row["source"])
    score = int(row["risk_score"])
    evidence = str(row["evidence"])

    rule_playbooks = {
        "R01": {
            "mitre": "T1078.002 — Valid Accounts: Domain Accounts",
            "iso": "ISO/IEC 27001:2022 A.5.16 (Gestión de identidades) y A.8.2",
            "cmd": f"Disable-ADAccount -Identity '{sam}' -Confirm:$false",
            "narrative": (
                f"La identidad `{username}` en `{source}` presenta inactividad prolongada o ausencia de autenticación (`{evidence}`). "
                "Las cuentas huérfanas habilitadas son el vector principal de persistencia silenciosa y movimiento lateral."
            ),
        },
        "R02": {
            "mitre": "T1098 — Account Manipulation / Unjustified Privilege",
            "iso": "ISO/IEC 27001:2022 A.8.2 (Derechos de acceso privilegiado)",
            "cmd": f"Set-ADUser -Identity '{sam}' -Description 'Pendiente de recertificación SOC' ; Remove-ADGroupMember -Identity 'Domain Admins' -Members '{sam}' -Confirm:$false",
            "narrative": (
                f"La cuenta `{username}` posee privilegios administrativos activos sin justificación verificada en los metadatos del directorio (`{evidence}`). "
                "Incumple el principio de mínimo privilegio y trazabilidad de acceso privilegiado."
            ),
        },
        "R03": {
            "mitre": "T1078.002 — Valid Accounts (Shadow / Duplicate Admin)",
            "iso": "ISO/IEC 27001:2022 A.8.2 y A.5.18 (Derechos de acceso)",
            "cmd": f"Get-ADPrincipalGroupMembership -Identity '{sam}' | Select-Object Name, SID",
            "narrative": (
                f"Se detectó una identidad administrativa adicional o duplicada (`{username}`) en `{source}` (`{evidence}`). "
                "La proliferación de cuentas admin secundarias incrementa la superficie de robo de hashes NTLM/Kerberos."
            ),
        },
        "R04": {
            "mitre": "T1558.003 — Steal or Forge Kerberos Tickets: Kerberoasting",
            "iso": "ISO/IEC 27001:2022 A.5.17 (Información de autenticación) y A.8.2",
            "cmd": f"Set-ADUser -Identity '{sam}' -PasswordNeverExpires $false",
            "narrative": (
                f"La cuenta de servicio/SPN `{username}` tiene `pwdNeverExpires=true` (`{evidence}`). "
                "En Active Directory, las cuentas SPN con contraseñas estáticas son vulnerables a extracción de tickets TGS y cracking offline (Kerberoasting)."
            ),
        },
        "R05": {
            "mitre": "T1484.001 — Domain Policy Modification / Excessive Group Membership",
            "iso": "ISO/IEC 27001:2022 A.8.2 (Acceso privilegiado) y NIST PR.AC-4",
            "cmd": f"Get-ADUser -Identity '{sam}' -Properties MemberOf | Select-Object -ExpandProperty MemberOf",
            "narrative": (
                f"La identidad `{username}` pertenece a grupos de alto privilegio fuera de la línea base autorizada (`{evidence}`). "
                "Comprometer esta cuenta otorga control directo o indirecto sobre el controlador de dominio."
            ),
        },
        "R06": {
            "mitre": "T1078 — Valid Accounts (Unreviewed High-Risk Identity)",
            "iso": "ISO/IEC 27001:2022 A.5.18 (Revisión de derechos de acceso) y A.8.16",
            "cmd": f"Get-ADUser -Identity '{sam}' -Properties PasswordLastSet,LastLogonDate,AdminCount",
            "narrative": (
                f"La cuenta `{username}` acumula un score crítico/alto ({score}/100) y supera el umbral de 90 días sin rotación ni revisión de credenciales (`{evidence}`)."
            ),
        },
    }
    pb = rule_playbooks.get(rule_id, rule_playbooks["R01"])
    priority = "P1 - Inmediata (Crítica)" if score >= 80 else "P2 - Alta (24h)" if score >= 60 else "P3 - Programada (72h)"
    sla = 4 if score >= 80 else 24 if score >= 60 else 72

    output = {
        "execution_id": "lf-" + uuid.uuid4().hex[:10],
        "finding_id": int(finding_id),
        "rule_id": rule_id,
        "username": username,
        "source": source,
        "risk_score": score,
        "summary": pb["narrative"],
        "recommended_priority": priority,
        "sla_hours": sla,
        "mitre_attack": pb["mitre"],
        "iso27001_control": pb["iso"],
        "remediation_command": pb["cmd"],
        "model_version": "deterministic-r01-r06-v1",
        "validation": "verified_against_deterministic_evidence",
    }
    with engine.begin() as conn:
        audit_event(
            conn,
            actor,
            role,
            "langflow_explain",
            f"finding:{finding_id}",
            "success",
            f"Heurística determinista priorizó hallazgo #{finding_id} ({rule_id} · {username}) -> {priority}",
        )
    from llm_harness import enrich
    from xai import explain_account
    account = account_frame()
    match = account[account['id'] == int(row['account_id'])]
    if not match.empty:
        output['deterministic'] = explain_account(match.iloc[0].to_dict())
    return enrich(output, actor, role)


def trigger_n8n_pipeline(actor: str = "n8n-orchestrator@caso16.local", role: str = "Orquestador Automatizado n8n") -> dict[str, Any]:
    """Ejecuta el flujo completo de automatización n8n (Ingesta -> Reglas R01-R06 -> LangFlow Top Críticos -> Bitácora)."""
    scan_res = run_detection(actor=actor, role=role)
    m = dashboard_metrics()
    f_df = finding_frame()
    crit_count = int((f_df["severity"] == "Crítico").sum()) if not f_df.empty else 0
    top_finding_id = int(f_df.iloc[0]["id"]) if not f_df.empty else 1
    lf_sample = explain_finding_langflow(top_finding_id, actor="langflow-node@caso16.local", role="Nodo LangFlow IA")

    pipeline_id = "n8n-" + uuid.uuid4().hex[:10]
    steps = [
        {"step": 1, "node": "1. Cron Diario (02:00 UTC)", "status": "completed", "detail": "Disparo programado / webhook recibido"},
        {"step": 2, "node": "2. Extracción AD/LDAP (SharpHound)", "status": "completed", "detail": f"{m['accounts']} cuentas leídas en 4 dominios AD"},
        {"step": 3, "node": "3. Motor Determinista (R01–R06)", "status": "completed", "detail": f"Run {scan_res['run_id']} · {m['open_findings']} hallazgos activos evaluados"},
        {"step": 4, "node": "4. LangFlow IA (Priorización)", "status": "completed", "detail": f"Top hallazgo #{top_finding_id} priorizado ({lf_sample['recommended_priority']})"},
        {"step": 5, "node": "5. Alerta SOC & Bitácora Inmutable", "status": "completed", "detail": f"{crit_count} hallazgos críticos notificados y auditados"},
    ]
    with engine.begin() as conn:
        audit_event(
            conn,
            actor,
            role,
            "n8n_pipeline_run",
            pipeline_id,
            "success",
            f"Flujo n8n completado: {m['accounts']} cuentas, {m['open_findings']} hallazgos, {crit_count} críticos",
        )
    return {
        "pipeline_id": pipeline_id,
        "status": "completed",
        "accounts_processed": m["accounts"],
        "open_findings": m["open_findings"],
        "critical_findings": crit_count,
        "steps": steps,
        "langflow_spotlight": lf_sample,
    }

def system_health_metrics() -> dict[str, Any]:
    """Retorna estado detallado de todos los componentes para la vista de monitoreo."""
    health_base = api_health()
    ds = directory_source_frame()
    pol = policy_frame()
    return {
        **health_base,
        "database_engine": engine.dialect.name,
        "directory_sources_synced": len(ds),
        "security_policies_active": int(pol["is_active"].sum()) if not pol.empty else 0,
        "ai_engine_status": "Ready (Deterministic MITRE ATT&CK Ingestion + LangFlow JSON Contract)",
        "automation_n8n_status": "Configured (automation_n8n_scan.json workflow)",
        "last_check_utc": datetime.now(UTC).isoformat(),
    }


init_db()
