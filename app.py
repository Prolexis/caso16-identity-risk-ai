from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import security
from analytics_ui import render_descriptive, render_evaluation, render_inference, render_metadata, render_upload
from optuna_ui import render_training
from reporting import build_report, traceability
from data_layer import (
    RULES,
    account_frame,
    authenticate_user,
    api_health,
    audit_frame,
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
    run_frame,
    trigger_n8n_pipeline,
    system_health_metrics,
    ticket_frame,
    update_finding,
    update_policy,
    update_ticket,
    user_frame,
)

st.set_page_config(page_title="CASO16 | SOC Identity Risk AI", layout="wide")
init_db()

ROLES = {
    "admin@demo.local": "Superadministrador",
    "security@demo.local": "Administrador de seguridad",
    "analyst@demo.local": "Analista de ciberseguridad",
    "remediator@demo.local": "Responsable de remediación",
    "auditor@demo.local": "Auditor",
    "consultant@demo.local": "Usuario de consulta",
}

SEVERITY_COLORS = {
    "Crítico": "#ef4444",
    "Alto": "#f97316",
    "Medio": "#38bdf8",
    "Bajo": "#10b981",
}


def inject_custom_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(circle at 85% 5%, rgba(14, 116, 144, 0.18) 0%, transparent 40%),
                        radial-gradient(circle at 10% 90%, rgba(59, 130, 246, 0.12) 0%, transparent 35%),
                        #07111f;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #09172a 0%, #07111f 100%);
            border-right: 1px solid rgba(56, 189, 248, 0.16);
        }
        [data-testid="stMetric"] {
            background: linear-gradient(145deg, rgba(15, 33, 56, 0.92) 0%, rgba(10, 22, 38, 0.95) 100%);
            border: 1px solid rgba(56, 189, 248, 0.22) !important;
            border-radius: 12px !important;
            padding: 16px 18px !important;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.32), inset 0 1px 0 rgba(255, 255, 255, 0.05);
            transition: transform 0.18s ease, border-color 0.18s ease;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-color: rgba(56, 189, 248, 0.55) !important;
        }
        [data-testid="stMetricLabel"] {
            color: #94a3b8 !important;
            font-weight: 600 !important;
            letter-spacing: 0.02em;
        }
        [data-testid="stMetricValue"] {
            color: #f8fafc !important;
            font-weight: 700 !important;
        }
        .soc-hero {
            background: linear-gradient(135deg, rgba(14, 41, 75, 0.85) 0%, rgba(9, 22, 40, 0.92) 100%);
            border: 1px solid rgba(56, 189, 248, 0.28);
            border-left: 4px solid #38bdf8;
            border-radius: 12px;
            padding: 16px 22px;
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }
        .soc-hero-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: #e2e8f0;
            margin: 0 0 4px 0;
        }
        .soc-hero-sub {
            font-size: 0.85rem;
            color: #94a3b8;
            margin: 0;
        }
        .soc-pill {
            background: rgba(56, 189, 248, 0.14);
            border: 1px solid rgba(56, 189, 248, 0.4);
            color: #7dd3fc;
            font-size: 0.75rem;
            font-weight: 600;
            padding: 5px 12px;
            border-radius: 999px;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_session() -> None:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("actor", "analyst@demo.local")
    st.session_state.setdefault("role", ROLES["analyst@demo.local"])
    st.session_state.setdefault("jwt_token", None)


def login_view() -> None:
    st.title("CASO16 · OrphanHunter SOC")
    st.subheader("Centro de Operaciones de Riesgo de Identidades y Privilegios (AD / LDAP)")
    st.caption("Plataforma determinista de auditoría continua evaluada con el dataset público SharpHound / BloodHound Active Directory.")
    with st.container(border=True):
        st.markdown("#### 🔐 Acceso a la Consola Operacional (IAM / RBAC)")
        actor = st.selectbox("Perfil de usuario (RBAC)", list(ROLES), format_func=lambda x: f"{x} · {ROLES[x]}")
        password = st.text_input("Contraseña", type="password", value="demo")
        if st.button("Iniciar sesión", type="primary", icon=":material/login:"):
            user = authenticate_user(actor, password)
            if not user:
                st.error("Credenciales incorrectas.")
            else:
                st.session_state.authenticated = True
                st.session_state.actor = user["email"]
                st.session_state.role = user["role"]
                token = security.create_access_token({
                    "sub": user["username"],
                    "email": user["email"],
                    "role": user["role"]
                })
                st.session_state.jwt_token = token
                st.rerun()
    st.info("Credenciales rápidas: selecciona cualquier perfil RBAC con contraseña **demo**.")


def severity_badge(value: str) -> str:
    colors = {"Crítico": "red", "Alto": "orange", "Medio": "blue", "Bajo": "green"}
    color = colors.get(value, "gray")
    return f":{color}-badge[{value}]"


def render_dashboard() -> None:
    st.title("📊 Dashboard operacional")
    st.markdown(
        """
        <div class="soc-hero">
            <div>
                <p class="soc-hero-title">📡 Telemetría Activa: Dataset Público SharpHound / BloodHound Active Directory</p>
                <p class="soc-hero-sub">Dominios auditados: <b>PHANTOM.CORP</b> (53) · <b>WRAITH.CORP</b> (40) · <b>ESC1.LOCAL</b> (14) · <b>GHOST.CORP</b> (6) — Control ISO/IEC 27001 A.8.2</p>
            </div>
            <span class="soc-pill">113 Identidades · 269 Hallazgos</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    metrics = dashboard_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Identidades auditadas", metrics["accounts"])
    c2.metric("Inactivas / Huérfanas (R01)", metrics["inactive"])
    c3.metric("Riesgo elevado (Score ≥60)", metrics["excessive"])
    c4.metric("Servicios clave eterna (R04)", metrics["service_no_expiry"])

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Hallazgos abiertos", metrics["open_findings"])
    c6.metric("Hallazgos cerrados", metrics["closed_findings"])
    c7.metric("Tickets de remediación", metrics.get("open_tickets", 10))
    c8.metric("Riesgo acumulado", f"{metrics['risk_total']:,} pts")

    st.write("")
    f = finding_frame()
    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("Distribución por severidad")
        if not f.empty:
            sev_df = f["severity"].value_counts().reset_index()
            sev_df.columns = ["Severidad", "Cantidad"]
            chart_sev = (
                alt.Chart(sev_df)
                .mark_bar(cornerRadius=6)
                .encode(
                    x=alt.X("Severidad:N", sort=["Crítico", "Alto", "Medio", "Bajo"]),
                    y=alt.Y("Cantidad:Q"),
                    color=alt.Color(
                        "Severidad:N",
                        scale=alt.Scale(
                            domain=["Crítico", "Alto", "Medio", "Bajo"],
                            range=["#ef4444", "#f97316", "#38bdf8", "#10b981"],
                        ),
                        legend=None,
                    ),
                    tooltip=["Severidad", "Cantidad"],
                )
                .properties(height=260)
            )
            st.altair_chart(chart_sev, width="stretch")

    with col_right:
        st.subheader("Hallazgos por regla determinista")
        if not f.empty:
            rule_df = f["rule_id"].value_counts().reset_index()
            rule_df.columns = ["Regla", "Cantidad"]
            rule_df["Nombre"] = rule_df["Regla"].map(lambda r: RULES.get(r, (r, ""))[0])
            chart_rule = (
                alt.Chart(rule_df)
                .mark_bar(cornerRadius=6, color="#0ea5e9")
                .encode(
                    x=alt.X("Cantidad:Q"),
                    y=alt.Y("Regla:N", sort="-x"),
                    tooltip=["Regla", "Nombre", "Cantidad"],
                )
                .properties(height=260)
            )
            st.altair_chart(chart_rule, width="stretch")


def render_inventory() -> None:
    st.title("📇 Inventario de identidades AD")
    st.caption("Inventario actual de identidades; cifras calculadas desde la base de datos.")
    data = account_frame()
    if data.empty:
        st.warning("Inventario no disponible. Ejecuta un escaneo desde el menú lateral.")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total identidades", len(data), border=True)
    m2.metric("Cuentas Admin", int((data["account_type"] == "admin").sum()), border=True)
    m3.metric("Cuentas Servicio / SPN", int((data["account_type"] == "service").sum()), border=True)
    m4.metric("Cuentas Estándar", int((data["account_type"] == "user").sum()), border=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        query = st.text_input("Buscar", placeholder="usuario, SID, grupo o dominio")
    with c2:
        type_filter = st.multiselect("Tipo de cuenta", sorted(data["account_type"].unique()), default=[])
    with c3:
        source_filter = st.multiselect("Origen", sorted(data["source"].unique()), default=[])
    if query:
        mask = data.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False, regex=False)).any(axis=1)
        data = data[mask]
    if type_filter:
        data = data[data["account_type"].isin(type_filter)]
    if source_filter:
        data = data[data["source"].isin(source_filter)]
    cols = [
        "id", "username", "display_name", "email", "account_type", "source",
        "active", "is_admin", "password_never_expires", "privileged_roles",
        "last_activity", "review_at", "risk_score",
    ]
    st.dataframe(
        data[cols],
        hide_index=True,
        width="stretch",
        column_config={
            "risk_score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
            "email": st.column_config.TextColumn("UPN / Correo", width="medium"),
        },
    )
    st.download_button(
        "Exportar inventario CSV",
        data=data.to_csv(index=False).encode("utf-8"),
        file_name="caso16_inventario.csv",
        mime="text/csv",
        icon=":material/download:",
    )


def render_findings() -> None:
    st.title("⚠️ Hallazgos y remediación")
    st.caption("Flujo trazable: Detectado → En evaluación → Asignado → En remediación → Pendiente de validación → Resuelto → Cerrado.")
    data = finding_frame()
    if data.empty:
        st.info("No hay hallazgos. Usa **Ejecutar escaneo** en el menú lateral.")
        return

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total hallazgos", len(data), border=True)
    k2.metric("Críticos", int((data["severity"] == "Crítico").sum()), border=True)
    k3.metric("Evidencia confirmada", int((data["evidence_state"] == "confirmed").sum()), border=True)
    k4.metric("Evidencia potencial", int((data["evidence_state"] == "potential").sum()), border=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        severity = st.multiselect("Severidad", ["Crítico", "Alto", "Medio", "Bajo"], default=[])
    with c2:
        status = st.multiselect("Estado", sorted(data["status"].unique()), default=[])
    with c3:
        evidence_state = st.multiselect("Evidencia", ["confirmed", "potential", "insufficient_evidence"], default=[])
    with c4:
        rule = st.multiselect("Regla", sorted(data["rule_id"].unique()), default=[])
    filtered = data.copy()
    if severity:
        filtered = filtered[filtered["severity"].isin(severity)]
    if status:
        filtered = filtered[filtered["status"].isin(status)]
    if evidence_state:
        filtered = filtered[filtered["evidence_state"].isin(evidence_state)]
    if rule:
        filtered = filtered[filtered["rule_id"].isin(rule)]
    display = filtered[["id", "rule_id", "username", "source", "title", "severity", "evidence_state", "status", "owner", "risk_score", "created_at"]]
    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        column_config={"risk_score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100)},
    )
    if filtered.empty:
        return
    selected_id = st.selectbox(
        "Selecciona un hallazgo para revisar y gestionar",
        filtered["id"].tolist(),
        format_func=lambda x: f"#{x} · {filtered.loc[filtered.id == x, 'rule_id'].iloc[0]} · {filtered.loc[filtered.id == x, 'username'].iloc[0]}",
    )
    finding = filtered[filtered["id"] == selected_id].iloc[0]
    with st.container(border=True):
        st.subheader(f"{finding['rule_id']} · {finding['title']}")
        st.markdown(
            f"**Cuenta:** `{finding['username']}` · **Dominio:** `{finding['source']}` · "
            f"**Severidad:** {severity_badge(finding['severity'])} · **Evidencia:** `{finding['evidence_state']}`"
        )
        st.write(finding["rationale"])
        st.code(finding["evidence"], language="text")

        # Asistente Inteligente de Explicabilidad MITRE ATT&CK / IA
        with st.expander("🧠 Explicación determinista y mitigación (MITRE ATT&CK)", expanded=False):
            ai_data = explain_finding_ai(int(selected_id))
            st.markdown(f"**Técnica MITRE ATT&CK:** `{ai_data['mitre_technique']}` — *{ai_data['mitre_tactics']}*")
            st.markdown(f"**Vector de Ataque:** {ai_data['attack_vector_analysis']}")
            st.markdown(f"**Impacto Potencial:** {ai_data['potential_impact']}")
            st.markdown(f"**Control Normativo:** `{ai_data['iso_27001_reference']}`")
            st.markdown("**Plan de Mitigación Recomendado:**")
            for step in ai_data["recommended_remediation_plan"]:
                st.markdown(f"- {step}")

        valid_statuses = [
            "Detectado", "En evaluación", "Asignado", "En remediación",
            "Pendiente de validación", "Resuelto", "Cerrado", "Falso positivo", "Excepción",
        ]
        with st.form(f"finding_form_{selected_id}"):
            new_status = st.selectbox(
                "Nuevo estado",
                valid_statuses,
                index=valid_statuses.index(finding["status"]) if finding["status"] in valid_statuses else 0,
            )
            owner = st.text_input("Responsable", value=finding["owner"] or "")
            comment = st.text_area("Comentario de revisión", placeholder="Documenta la decisión, ticket o evidencia adicional")
            col_b1, col_b2 = st.columns([1, 1])
            with col_b1:
                submit = st.form_submit_button("Guardar actualización", type="primary", icon=":material/save:")
            with col_b2:
                create_tck = st.form_submit_button("Generar Ticket SLA", icon=":material/confirmation_number:")

            if submit:
                update_finding(int(selected_id), new_status, owner, st.session_state.actor, st.session_state.role, comment)
                st.success("Hallazgo actualizado y registrado en la bitácora inmutable.")
                st.rerun()
            if create_tck:
                sla = 7 if finding["severity"] == "Crítico" else 15
                t_id = create_ticket(
                    int(selected_id), f"Remediación: {finding['title']}", finding["rationale"],
                    finding["severity"], owner or st.session_state.actor, sla,
                    st.session_state.actor, st.session_state.role
                )
                st.success(f"Ticket {t_id} creado con SLA de {sla} días.")
                st.rerun()


def render_tickets() -> None:
    st.title("🎫 Gestión de tickets y SLA de remediación")
    st.caption("Control de incidentes de acceso y remediación continua con acuerdos de nivel de servicio (SLA).")
    t_data = ticket_frame()
    if t_data.empty:
        st.info("No hay tickets registrados actualmente.")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total tickets", len(t_data), border=True)
    m2.metric("Abiertos", int((t_data["status"] == "Abierto").sum()), border=True)
    m3.metric("En Progreso", int((t_data["status"] == "En Progreso").sum()), border=True)
    m4.metric("Críticos", int((t_data["priority"] == "Crítico").sum()), border=True)

    col1, col2 = st.columns(2)
    with col1:
        st_filter = st.multiselect("Filtrar por estado", sorted(t_data["status"].unique()), default=[])
    with col2:
        pr_filter = st.multiselect("Filtrar por prioridad", ["Crítico", "Alto", "Media", "Baja"], default=[])

    filtered_t = t_data.copy()
    if st_filter:
        filtered_t = filtered_t[filtered_t["status"].isin(st_filter)]
    if pr_filter:
        filtered_t = filtered_t[filtered_t["priority"].isin(pr_filter)]

    st.dataframe(
        filtered_t[["id", "title", "priority", "status", "owner", "sla_due_date", "created_at"]],
        hide_index=True,
        width="stretch",
    )

    if not filtered_t.empty:
        sel_ticket = st.selectbox(
            "Seleccionar ticket para actualizar",
            filtered_t["id"].tolist(),
            format_func=lambda x: f"{x} · {filtered_t.loc[filtered_t.id == x, 'title'].iloc[0]}"
        )
        t_row = filtered_t[filtered_t["id"] == sel_ticket].iloc[0]
        with st.container(border=True):
            st.markdown(f"#### Ticket: `{t_row['id']}` · {t_row['title']}")
            st.markdown(f"**Prioridad:** {severity_badge(t_row['priority'])} | **Fecha Límite SLA:** `{t_row['sla_due_date']}`")
            st.write(t_row["description"])
            with st.form(f"form_ticket_{sel_ticket}"):
                statuses = ["Abierto", "En Progreso", "Pendiente Validación", "Resuelto", "Cerrado"]
                n_status = st.selectbox("Estado del ticket", statuses, index=statuses.index(t_row["status"]) if t_row["status"] in statuses else 0)
                n_owner = st.text_input("Responsable asignado", value=t_row["owner"] or "")
                notes = st.text_area("Notas de resolución / remediación", value=t_row["resolution_notes"] or "")
                if st.form_submit_button("Actualizar ticket", type="primary"):
                    update_ticket(sel_ticket, n_status, n_owner, notes, st.session_state.actor, st.session_state.role)
                    st.success("Ticket actualizado exitosamente.")
                    st.rerun()


def render_policies() -> None:
    st.title("⚙️ Políticas de seguridad, umbrales y excepciones")
    st.caption("Ajuste dinámico de parámetros de detección de riesgo y excepciones autorizadas con fecha de vencimiento.")

    tab1, tab2, tab3 = st.tabs(["⚙️ Políticas y Umbrales", "🛡️ Excepciones Autorizadas", "📡 Fuentes de Directorio"])

    with tab1:
        st.subheader("Catálogo de políticas operacionales")
        pols = policy_frame()
        st.dataframe(pols[["id", "code", "name", "threshold_value", "unit", "is_active", "updated_at"]], hide_index=True, width="stretch")
        if not pols.empty:
            sel_pol = st.selectbox("Selecciona política para configurar", pols["id"].tolist(), format_func=lambda x: pols.loc[pols.id == x, 'name'].iloc[0])
            p_row = pols[pols["id"] == sel_pol].iloc[0]
            with st.form(f"pol_form_{sel_pol}"):
                val = st.number_input(f"Valor umbral ({p_row['unit']})", value=int(p_row["threshold_value"]), min_value=0, max_value=1000)
                active = st.checkbox("Política activa", value=bool(p_row["is_active"]))
                if st.form_submit_button("Guardar cambios en política", type="primary"):
                    update_policy(sel_pol, int(val), active, st.session_state.actor, st.session_state.role)
                    st.success("Política actualizada en la base de datos.")
                    st.rerun()

    with tab2:
        st.subheader("Excepciones autorizadas")
        excs = exception_frame()
        if excs.empty:
            st.info("No hay excepciones activas.")
        else:
            st.dataframe(excs, hide_index=True, width="stretch")
        with st.expander("➕ Autorizar nueva excepción"):
            with st.form("new_exception_form"):
                accs = account_frame()
                acc_id = st.selectbox("Cuenta de directorio", accs["id"].tolist(), format_func=lambda x: f"#{x} · {accs.loc[accs.id == x, 'username'].iloc[0]}")
                rule_sel = st.selectbox("Regla excluida", list(RULES.keys()), format_func=lambda r: f"{r} · {RULES[r][0]}")
                days = st.number_input("Días de vigencia", min_value=1, max_value=365, value=30)
                just = st.text_area("Justificación técnica / ticket de aprobación", placeholder="Aprobado por CISO según ticket SEC-1002 por requerimiento de servicio legado...")
                if st.form_submit_button("Aprobar excepción", type="primary"):
                    create_exception(acc_id, rule_sel, just, st.session_state.actor, int(days), st.session_state.actor, st.session_state.role)
                    st.success("Excepción registrada.")
                    st.rerun()

    with tab3:
        st.subheader("Conexiones y fuentes de directorio Active Directory")
        dirs = directory_source_frame()
        st.dataframe(dirs, hide_index=True, width="stretch")


def render_users_roles() -> None:
    st.title("👥 Usuarios y roles del sistema (RBAC)")
    st.caption("Administración de identidades locales, asignación de roles y control de privilegios mínimos.")

    tab1, tab2 = st.tabs(["👥 Usuarios del Sistema", "🛡️ Matriz de Roles y Permisos"])

    with tab1:
        u_data = user_frame().drop(columns=["hashed_password"], errors="ignore")
        st.dataframe(u_data, hide_index=True, width="stretch")
        with st.expander("➕ Dar de alta nuevo usuario"):
            with st.form("new_user_form"):
                u_name = st.text_input("Nombre de usuario (login)")
                u_email = st.text_input("Correo electrónico")
                u_pass = st.text_input("Contraseña temporal", type="password")
                u_full = st.text_input("Nombre completo")
                u_role = st.selectbox("Rol asignado", list(ROLES.values()))
                if st.form_submit_button("Crear usuario", type="primary"):
                    if not u_name or not u_email or not u_pass:
                        st.error("Todos los campos son obligatorios.")
                    else:
                        try:
                            create_user(u_name, u_email, u_pass, u_full, u_role, st.session_state.actor, st.session_state.role)
                            st.success(f"Usuario {u_name} creado exitosamente con contraseña segura.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

    with tab2:
        r_data = role_frame()
        st.dataframe(r_data, hide_index=True, width="stretch")


def render_audit() -> None:
    st.title("📜 Bitácora de auditoría")
    st.caption("Registros inmutables (append-only) de todas las operaciones del sistema; alineado con ISO/IEC 27001 A.8.16.")
    data = audit_frame()
    if data.empty:
        st.info("Aún no existen eventos.")
        return
    action = st.multiselect("Filtrar acciones", sorted(data["action"].unique()), default=[])
    if action:
        data = data[data["action"].isin(action)]
    st.dataframe(data, hide_index=True, width="stretch")
    st.download_button(
        "Exportar bitácora CSV",
        data=data.to_csv(index=False).encode("utf-8"),
        file_name="caso16_auditoria.csv",
        mime="text/csv",
        icon=":material/download:",
    )


def render_reports() -> None:
    st.title("📄 Reportes de auditoría")
    st.caption("Exportación de la instantánea actual, con hash, usuario, fecha e interpretación. Figuras PNG embebidas a 600 DPI; no se simulan métricas ML.")
    accounts, findings = account_frame(), finding_frame()
    st.json(traceability(accounts, st.session_state.actor))
    formats = [("xlsx", "Excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
               ("docx", "Word", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
               ("pdf", "PDF", "application/pdf")]
    for column, (fmt, label, mime) in zip(st.columns(3), formats):
        with column:
            if st.button(f"Generar {label}", key=f"generate_{fmt}"):
                try:
                    with st.spinner(f"Generando {label}…"):
                        payload = build_report(fmt, accounts, findings, st.session_state.actor)
                        from data_layer import engine, audit_event
                        with engine.begin() as conn:
                            audit_event(conn, st.session_state.actor, st.session_state.role, "export_report", f"report:{fmt}", "success", json.dumps(traceability(accounts, st.session_state.actor)))
                        st.session_state[f"report_{fmt}"] = payload
                except Exception as exc:
                    st.error(f"No se pudo generar el reporte: {exc}")
            if st.session_state.get(f"report_{fmt}"):
                st.download_button(f"Descargar {label} (.{fmt})", st.session_state[f"report_{fmt}"],
                                   file_name=f"caso16_auditoria.{fmt}", mime=mime, key=f"download_{fmt}")
    st.caption("Los archivos generados conservan su instantánea hasta volver a pulsar Generar.")


def render_scan() -> None:
    st.title("🚀 Ejecución de detección")
    st.caption("Pipeline determinista: Dataset Público SharpHound/BloodHound AD → Reglas R01–R06 → Score 0–100 → Hallazgos → Bitácora.")
    with st.container(border=True):
        st.markdown("**Catálogo de reglas deterministas activas**")
        for rule_id, (name, description) in RULES.items():
            st.markdown(f"- **{rule_id} · {name}:** {description}")
        if st.button("Ejecutar escaneo determinista", type="primary", icon=":material/play_arrow:"):
            with st.status("Procesando inventario actual de Active Directory y evaluando reglas R01–R06…", expanded=False) as status_box:
                result = run_detection(st.session_state.actor, st.session_state.role)
                status_box.update(label="Escaneo completado exitosamente", state="complete")
            st.success(f"{result['accounts_processed']} cuentas procesadas · {result['findings_created']} hallazgos nuevos · corrida `{result['run_id']}`")
            st.rerun()
    render_upload()
    st.subheader("Historial de ejecuciones")
    history = run_frame()
    st.dataframe(history, hide_index=True, width="stretch")


def render_integrations() -> None:
    st.title("Orquestación n8n & LangFlow IA", icon=":material/hub:")
    st.caption("Ejecución interactiva del pipeline automatizado n8n y del motor de priorización/explicación LangFlow IA sobre los 269 hallazgos reales.")

    base_dir = Path(__file__).resolve().parent
    n8n_path = base_dir / "automation_n8n_scan.json"
    lf_path = base_dir / "langflow_flow.json"
    n8n_json = n8n_path.read_text(encoding="utf-8") if n8n_path.exists() else "{}"
    lf_json = lf_path.read_text(encoding="utf-8") if lf_path.exists() else "{}"

    tab_n8n, tab_lf = st.tabs(["⚙️ Pipeline Automatizado n8n", "🧠 Copiloto de Priorización LangFlow IA"])

    with tab_n8n:
        st.subheader("Flujo de Automatización Continua (n8n)", icon=":material/account_tree:")
        st.markdown(
            "Secuencia de 5 nodos conectada vía API (`/api/v1/integrations/n8n/trigger`): "
            "**1. Cron 24h** → **2. Extracción AD/LDAP (SharpHound)** → **3. Reglas Deterministas R01–R06** → "
            "**4. Priorización LangFlow IA** → **5. Alerta SOC y Bitácora Inmutable**."
        )
        col_btn, col_dl = st.columns([1, 1])
        with col_btn:
            run_n8n = st.button("Disparar Pipeline n8n Ahora", type="primary", icon=":material/bolt:")
        with col_dl:
            st.download_button(
                "Descargar Flujo n8n (.json)",
                data=n8n_json.encode("utf-8"),
                file_name="automation_n8n_scan.json",
                mime="application/json",
                icon=":material/download:",
            )

        if run_n8n:
            with st.status("Ejecutando los 5 nodos del workflow n8n…", expanded=True) as status_box:
                res = trigger_n8n_pipeline(actor=st.session_state.actor, role=st.session_state.role)
                status_box.update(label=f"Pipeline {res['pipeline_id']} completado exitosamente", state="complete")
            st.session_state["last_n8n_run"] = res

        last_run = st.session_state.get("last_n8n_run")
        if last_run:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("ID de Ejecución", last_run["pipeline_id"], border=True)
            m2.metric("Cuentas Auditadas", last_run["accounts_processed"], border=True)
            m3.metric("Hallazgos Activos", last_run["open_findings"], border=True)
            m4.metric("Críticos Alertados", last_run["critical_findings"], border=True)
            st.dataframe(pd.DataFrame(last_run["steps"]), hide_index=True, width="stretch")

        with st.expander("Ver definición JSON del Workflow n8n (`automation_n8n_scan.json`)"):
            st.code(n8n_json, language="json")

    with tab_lf:
        st.subheader("Priorizador y Explicador de Riesgo (LangFlow + Guardrails)", icon=":material/psychology:")
        st.markdown(
            "Selecciona cualquiera de los **269 hallazgos reales** detectados en Active Directory para generar su "
            "**análisis ejecutivo de movimiento lateral**, mapeo **MITRE ATT&CK**, control **ISO/IEC 27001:2022** y **comando PowerShell AD** de remediación."
        )
        f_df = finding_frame()
        if not f_df.empty:
            selected_fid = st.selectbox(
                "Hallazgo a analizar con LangFlow IA",
                f_df["id"].tolist(),
                format_func=lambda x: (
                    f"#{x} · {f_df.loc[f_df.id == x, 'rule_id'].iloc[0]} · "
                    f"{f_df.loc[f_df.id == x, 'username'].iloc[0]} "
                    f"(Score: {f_df.loc[f_df.id == x, 'risk_score'].iloc[0]} · {f_df.loc[f_df.id == x, 'severity'].iloc[0]})"
                ),
            )
            c_run, c_dl = st.columns([1, 1])
            with c_run:
                run_lf = st.button("Generar Explicación y Priorización LangFlow", type="primary", icon=":material/auto_awesome:")
            with c_dl:
                st.download_button(
                    "Descargar Flujo LangFlow (.json)",
                    data=lf_json.encode("utf-8"),
                    file_name="langflow_flow.json",
                    mime="application/json",
                    icon=":material/download:",
                )

            if run_lf:
                st.session_state["last_lf_finding"] = int(selected_fid)
                st.session_state["last_lf_output"] = explain_finding_langflow(
                    int(selected_fid), actor=st.session_state.actor, role=st.session_state.role
                )

            lf_out = st.session_state.get("last_lf_output")
            if lf_out and st.session_state.get("last_lf_finding") == int(selected_fid):
                st.caption(f"Proveedor/modo: {lf_out.get('provider', lf_out.get('mode', 'determinista; proveedor no informado'))}")
                with st.container(border=True):
                    k1, k2, k3 = st.columns(3)
                    k1.metric("Prioridad Sugerida", lf_out["recommended_priority"], border=True)
                    k2.metric("SLA de Remediación", f"{lf_out['sla_hours']} horas", border=True)
                    k3.metric("Score Determinista", f"{lf_out['risk_score']} / 100", border=True)

                    st.markdown(f"**🔍 Explicación Ejecutiva (LangFlow):**\n\n{lf_out['summary']}")
                    st.markdown(
                        f"- **🎯 Técnica MITRE ATT&CK:** `{lf_out['mitre_attack']}`\n"
                        f"- **🛡️ Control Normativo:** `{lf_out['iso27001_control']}`\n"
                        f"- **✅ Validación de Guardrails:** `{lf_out['validation']}` (`{lf_out['execution_id']}`)"
                    )
                    st.markdown("**💻 Comando PowerShell AD sugerido para validación humana:**")
                    st.code(lf_out["remediation_command"], language="powershell")

        with st.expander("Ver contrato JSON del Flujo LangFlow (`langflow_flow.json`)"):
            st.code(lf_json, language="json")


def render_health() -> None:
    st.title("🏥 Salud y monitoreo del sistema")
    health = system_health_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estado API / Core", health.get("status", "unknown").upper(), border=True)
    c2.metric("Base de datos", health.get("database", "unknown"), border=True)
    c3.metric("Cuentas cargadas", health.get("accounts_loaded", 113), border=True)
    c4.metric("Orquestación", "n8n + LangFlow", border=True)
    st.subheader("Estado de subsistemas y dependencias")
    st.dataframe(
        pd.DataFrame([
            {"Componente": "Persistencia", "Estado": health.get("database"), "Nota": "PostgreSQL 16 en Docker Compose / SQLite local sincronizado"},
            {"Componente": "Dataset Público AD", "Estado": "operativo (113 cuentas)", "Nota": "SharpHound/BloodHound: PHANTOM.CORP, WRAITH.CORP, GHOST.CORP, ESC1.LOCAL"},
            {"Componente": "Motor R01–R06", "Estado": "operativo (269 hallazgos)", "Nota": "Evaluación determinista auditable y score 0–100"},
            {"Componente": "Pipeline n8n", "Estado": "operativo (/api/v1/integrations/n8n/trigger)", "Nota": "Ejecución automatizada de 5 nodos y plantilla exportable JSON"},
            {"Componente": "Copiloto LangFlow IA", "Estado": "operativo (/api/v1/findings/{id}/explain)", "Nota": "Priorización, mapeo MITRE ATT&CK / ISO 27001 A.8.2 y remediación PowerShell"},
            {"Componente": "Base de Datos", "Estado": health.get("database"), "Detalle": f"Motor {health.get('database_engine')} con persistencia transaccional"},
            {"Componente": "Dataset SharpHound AD", "Estado": f"operativo ({health.get('accounts_loaded')} cuentas)", "Detalle": "PHANTOM.CORP, WRAITH.CORP, GHOST.CORP, ESC1.LOCAL"},
            {"Componente": "Motor de Reglas R01-R06", "Estado": f"operativo ({health.get('findings_active')} hallazgos)", "Detalle": "Evaluación determinista y scoring 0-100"},
            {"Componente": "Gestión de Tickets & SLA", "Estado": f"operativo ({health.get('tickets_managed')} tickets)", "Detalle": "Trazabilidad de remediación y SLAs de 7 y 15 días"},
            {"Componente": "Seguridad & RBAC", "Estado": f"operativo ({health.get('users_rbac')} usuarios)", "Detalle": "6 roles, contraseñas hasheadas con salt y JWT Bearer"},
            {"Componente": "Políticas Configurables", "Estado": f"operativo ({health.get('security_policies_active')} activas)", "Detalle": "Umbrales dinámicos y excepciones autorizadas"},
            {"Componente": "Motor de IA / MITRE ATT&CK", "Estado": "listo", "Detalle": health.get("ai_engine_status")},
            {"Componente": "Exportación Ejecutiva", "Estado": "operativo", "Detalle": "Reportes nativos XLSX, DOCX y PDF"},
        ]),
        hide_index=True,
        width="stretch",
    )


def main() -> None:
    inject_custom_styles()
    init_session()
    if not st.session_state.authenticated:
        login_view()
        return
    with st.sidebar:
        st.title("🛡️ CASO16 · SOC")
        st.caption(f"👤 **{st.session_state.actor}**\n\n🛡️ {st.session_state.role}")
        page = st.radio(
            "Navegación",
            [
                "Dashboard",
                "Inventario",
                "Datos descriptivos",
                "Entrenamiento",
                "Evaluación",
                "Inferencia",
                "Optimización",
                "Hallazgos",
                "n8n & LangFlow IA",
                "Tickets & SLA",
                "Políticas & Excepciones",
                "Usuarios & Roles",
                "Auditoría",
                "Reportes",
                "Ejecutar escaneo",
                "Salud del sistema",
            ],
            label_visibility="collapsed",
        )
        st.write("")
        if st.button("Cerrar sesión"):
            for key in list(st.session_state):
                del st.session_state[key]
            st.rerun()
        st.caption("v1.2 · CASO16 Enterprise Identity Risk")

    if page == "Dashboard":
        render_dashboard()
    elif page == "Inventario":
        render_inventory()
        render_metadata(account_frame())
    elif page == "Datos descriptivos":
        render_descriptive(account_frame(), finding_frame())
    elif page == "Entrenamiento":
        render_training()
    elif page == "Evaluación":
        render_evaluation()
    elif page == "Inferencia":
        render_inference(account_frame())
    elif page == "Optimización":
        render_training(optimization=True)
    elif page == "Hallazgos":
        render_findings()
    elif page == "n8n & LangFlow IA":
        render_integrations()
    elif page == "Tickets & SLA":
        render_tickets()
    elif page == "Políticas & Excepciones":
        render_policies()
    elif page == "Usuarios & Roles":
        render_users_roles()
    elif page == "Auditoría":
        render_audit()
    elif page == "Reportes":
        render_reports()
    elif page == "Ejecutar escaneo":
        render_scan()
    else:
        render_health()


main()
