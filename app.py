from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from data_layer import (
    RULES,
    account_frame,
    api_health,
    audit_frame,
    dashboard_metrics,
    explain_finding_langflow,
    finding_frame,
    init_db,
    run_detection,
    run_frame,
    trigger_n8n_pipeline,
    update_finding,
)

st.set_page_config(page_title="CASO16 | SOC Identity Risk AI", page_icon=":material/security:", layout="wide")
init_db()

ROLES = {
    "analyst@demo.local": "Analista de ciberseguridad",
    "security@demo.local": "Administrador de seguridad",
    "auditor@demo.local": "Auditor",
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
        /* Fondo y contenedores estilo SOC Enterprise */
        .stApp {
            background: radial-gradient(circle at 85% 5%, rgba(14, 116, 144, 0.18) 0%, transparent 40%),
                        radial-gradient(circle at 10% 90%, rgba(59, 130, 246, 0.12) 0%, transparent 35%),
                        #07111f;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #09172a 0%, #07111f 100%);
            border-right: 1px solid rgba(56, 189, 248, 0.16);
        }
        /* Tarjetas de métricas (KPIs) con borde luminoso y sombra */
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
        /* Banner hero superior */
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


def login_view() -> None:
    st.title("CASO16 · OrphanHunter SOC")
    st.subheader("Centro de Operaciones de Riesgo de Identidades y Privilegios (AD / LDAP)")
    st.caption("Plataforma determinista de auditoría continua evaluada con el dataset público SharpHound / BloodHound Active Directory.")
    with st.container(border=True):
        st.markdown("#### 🔐 Acceso a la Consola Operacional")
        actor = st.selectbox("Perfil de usuario (RBAC)", list(ROLES), format_func=lambda x: f"{x} · {ROLES[x]}")
        password = st.text_input("Contraseña", type="password", value="demo")
        if st.button("Iniciar sesión", type="primary", icon=":material/login:"):
            if password != "demo":
                st.error("Credenciales de demostración incorrectas.")
            else:
                st.session_state.authenticated = True
                st.session_state.actor = actor
                st.session_state.role = ROLES[actor]
                st.rerun()
    st.info("Credenciales de acceso rápido: selecciona cualquier perfil RBAC con contraseña **demo**.")


def severity_badge(value: str) -> str:
    colors = {"Crítico": "red", "Alto": "orange", "Medio": "blue", "Bajo": "green"}
    color = colors.get(value, "gray")
    return f":{color}-badge[{value}]"


def render_dashboard() -> None:
    st.title("Dashboard operacional", icon=":material/dashboard:")
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
    cols = st.columns(4)
    cards = [
        ("Cuentas inventariadas", metrics["accounts"], "4 dominios AD"),
        ("Inactivas / huérfanas", metrics["inactive"], "Umbral R01: 90 días"),
        ("Riesgo alto o crítico", metrics["excessive"], "Score determinista ≥ 60"),
        ("Servicios sin expiración", metrics["service_no_expiry"], "Regla R04"),
    ]
    for col, (label, value, delta) in zip(cols, cards):
        with col:
            st.metric(label, value, delta, border=True)

    cols2 = st.columns(4)
    secondary = [
        ("Hallazgos abiertos", metrics["open_findings"]),
        ("Hallazgos cerrados", metrics["closed_findings"]),
        ("Riesgo acumulado", metrics["risk_total"]),
        ("Motor de análisis", "Determinista R01–R06"),
    ]
    for col, (label, value) in zip(cols2, secondary):
        with col:
            st.metric(label, value, border=True)

    accounts = account_frame()
    findings = finding_frame()

    # Fila 1 de gráficos: Severidad (Donut) + Hallazgos por Regla (Barras Horizontales)
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.subheader("Distribución de severidad", icon=":material/donut_large:")
            if findings.empty:
                st.info("Aún no hay hallazgos. Ejecuta un escaneo determinista.")
            else:
                sev_df = (
                    findings.groupby("severity")
                    .size()
                    .reindex(["Crítico", "Alto", "Medio", "Bajo"], fill_value=0)
                    .reset_index(name="cantidad")
                )
                donut = (
                    alt.Chart(sev_df)
                    .mark_arc(innerRadius=62, outerRadius=108, cornerRadius=6)
                    .encode(
                        theta=alt.Theta("cantidad:Q", title="Hallazgos"),
                        color=alt.Color(
                            "severity:N",
                            scale=alt.Scale(
                                domain=["Crítico", "Alto", "Medio", "Bajo"],
                                range=["#ef4444", "#f97316", "#38bdf8", "#10b981"],
                            ),
                            legend=alt.Legend(title="Severidad", orient="right"),
                        ),
                        tooltip=[
                            alt.Tooltip("severity:N", title="Severidad"),
                            alt.Tooltip("cantidad:Q", title="Hallazgos"),
                        ],
                    )
                    .properties(height=270)
                )
                st.altair_chart(donut, width="stretch")

    with right:
        with st.container(border=True):
            st.subheader("Hallazgos por regla determinista (R01–R06)", icon=":material/rule:")
            if findings.empty:
                st.info("Sin datos de reglas todavía.")
            else:
                rule_df = (
                    findings.groupby(["rule_id", "title", "severity"])
                    .size()
                    .reset_index(name="hallazgos")
                    .sort_values("rule_id")
                )
                rule_df["etiqueta"] = rule_df["rule_id"] + " · " + rule_df["title"]
                bars_rule = (
                    alt.Chart(rule_df)
                    .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6, height=26)
                    .encode(
                        x=alt.X("hallazgos:Q", title="Cantidad de hallazgos"),
                        y=alt.Y("etiqueta:N", sort="-x", title=None),
                        color=alt.Color(
                            "severity:N",
                            scale=alt.Scale(
                                domain=["Crítico", "Alto", "Medio", "Bajo"],
                                range=["#ef4444", "#f97316", "#38bdf8", "#10b981"],
                            ),
                            legend=None,
                        ),
                        tooltip=[
                            alt.Tooltip("rule_id:N", title="Código"),
                            alt.Tooltip("title:N", title="Regla"),
                            alt.Tooltip("severity:N", title="Severidad"),
                            alt.Tooltip("hallazgos:Q", title="Total"),
                        ],
                    )
                    .properties(height=270)
                )
                st.altair_chart(bars_rule, width="stretch")

    # Fila 2 de gráficos: Top 12 Cuentas de Mayor Riesgo + Exposición por Dominio Active Directory
    g_left, g_right = st.columns(2)
    with g_left:
        with st.container(border=True):
            st.subheader("Top 12 identidades con mayor riesgo", icon=":material/monitoring:")
            if not accounts.empty:
                top_acc = accounts.head(12).copy()
                top_chart = (
                    alt.Chart(top_acc)
                    .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
                    .encode(
                        x=alt.X("risk_score:Q", title="Risk Score (0–100)", scale=alt.Scale(domain=[0, 100])),
                        y=alt.Y("username:N", sort="-x", title=None),
                        color=alt.Color(
                            "account_type:N",
                            scale=alt.Scale(
                                domain=["admin", "service", "user"],
                                range=["#f43f5e", "#a855f7", "#38bdf8"],
                            ),
                            legend=alt.Legend(title="Tipo", orient="top"),
                        ),
                        tooltip=[
                            alt.Tooltip("username:N", title="Cuenta"),
                            alt.Tooltip("account_type:N", title="Tipo"),
                            alt.Tooltip("source:N", title="Dominio"),
                            alt.Tooltip("risk_score:Q", title="Score"),
                            alt.Tooltip("privileged_roles:N", title="Grupos"),
                        ],
                    )
                    .properties(height=290)
                )
                st.altair_chart(top_chart, width="stretch")

    with g_right:
        with st.container(border=True):
            st.subheader("Hallazgos por dominio Active Directory", icon=":material/domain:")
            if not findings.empty:
                dom_df = (
                    findings.groupby(["source", "severity"])
                    .size()
                    .reset_index(name="total")
                )
                dom_chart = (
                    alt.Chart(dom_df)
                    .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                    .encode(
                        x=alt.X("source:N", title="Dominio AD", axis=alt.Axis(labelAngle=-15)),
                        y=alt.Y("total:Q", title="Hallazgos detectados"),
                        color=alt.Color(
                            "severity:N",
                            scale=alt.Scale(
                                domain=["Crítico", "Alto", "Medio", "Bajo"],
                                range=["#ef4444", "#f97316", "#38bdf8", "#10b981"],
                            ),
                            legend=alt.Legend(title="Severidad", orient="top"),
                        ),
                        tooltip=[
                            alt.Tooltip("source:N", title="Dominio"),
                            alt.Tooltip("severity:N", title="Severidad"),
                            alt.Tooltip("total:Q", title="Hallazgos"),
                        ],
                    )
                    .properties(height=290)
                )
                st.altair_chart(dom_chart, width="stretch")

    with st.container(border=True):
        st.subheader("Hallazgos prioritarios (Top 15)", icon=":material/priority_high:")
        if findings.empty:
            st.caption("Sin datos todavía.")
        else:
            view = findings[["id", "rule_id", "username", "source", "title", "severity", "evidence_state", "status", "risk_score"]].head(15).copy()
            st.dataframe(
                view,
                hide_index=True,
                width="stretch",
                column_config={
                    "risk_score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100),
                },
            )


def render_inventory() -> None:
    st.title("Inventario de identidades", icon=":material/manage_accounts:")
    st.caption("Atributos reales extraídos del dataset público SharpHound / BloodHound Active Directory (113 cuentas en 4 dominios).")
    data = account_frame()

    # Resumen rápido de tipos de cuenta
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
        mask = data.astype(str).apply(lambda col: col.str.contains(query, case=False, na=False)).any(axis=1)
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
    st.title("Hallazgos y remediación", icon=":material/assignment_late:")
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
            if st.form_submit_button("Guardar actualización", type="primary", icon=":material/save:"):
                update_finding(int(selected_id), new_status, owner, st.session_state.actor, st.session_state.role, comment)
                st.success("Hallazgo actualizado y registrado en la bitácora inmutable.")
                st.rerun()


def render_audit() -> None:
    st.title("Bitácora de auditoría", icon=":material/history:")
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
    st.title("Reportes trazables", icon=":material/description:")
    st.caption("Formatos ejecutivos generados en tiempo real desde la base persistente: Excel (.xlsx), Word (.docx) y PDF (.pdf).")
    accounts = account_frame()
    findings = finding_frame()
    audit = audit_frame()
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    m = dashboard_metrics()

    c1, c2, c3 = st.columns(3)
    c1.metric("Cuentas incluidas", m["accounts"], border=True)
    c2.metric("Hallazgos documentados", len(findings), border=True)
    c3.metric("Eventos de auditoría", len(audit), border=True)

    st.write(f"Emisor: **{st.session_state.actor}** ({st.session_state.role}) · Fecha de corte: **{generated}**")
    if st.button("Registrar generación en bitácora", icon=":material/history:"):
        from data_layer import audit_event, engine
        with engine.begin() as conn:
            audit_event(conn, st.session_state.actor, st.session_state.role, "generate_report", "reports", "success", "Paquete de reportes ejecutivos solicitado desde la UI")
        st.success("Evento de generación registrado en la bitácora.")

    xlsx = io.BytesIO()
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        accounts_export = accounts.copy()
        findings_export = findings.copy()
        audit_export = audit.copy()
        for df_exp in (accounts_export, findings_export, audit_export):
            for col in df_exp.columns:
                if isinstance(df_exp[col].dtype, pd.DatetimeTZDtype):
                    df_exp[col] = df_exp[col].dt.tz_localize(None)
                elif df_exp[col].dtype == "object":
                    df_exp[col] = df_exp[col].apply(
                        lambda v: v.replace(tzinfo=None) if isinstance(v, datetime) and v.tzinfo is not None else v
                    )
        accounts_export.to_excel(writer, index=False, sheet_name="Inventario")
        findings_export.to_excel(writer, index=False, sheet_name="Hallazgos")
        audit_export.to_excel(writer, index=False, sheet_name="Auditoria")
    xlsx.seek(0)

    from docx import Document
    doc = Document()
    doc.add_heading("CASO16 — Reporte ejecutivo de riesgos", 0)
    doc.add_paragraph(f"Origen: Dataset público SharpHound/BloodHound AD (4 dominios) | Emisor: {st.session_state.actor} | Generado: {generated}")
    doc.add_heading("Resumen", level=1)
    doc.add_paragraph(f"{m['accounts']} cuentas inventariadas, {m['open_findings']} hallazgos abiertos, riesgo acumulado {m['risk_total']}.")
    doc.add_heading("Hallazgos prioritarios", level=1)
    table = doc.add_table(rows=1, cols=5)
    for cell, text in zip(table.rows[0].cells, ["Regla", "Cuenta", "Severidad", "Estado", "Score"]):
        cell.text = text
    for _, row in findings.head(25).iterrows():
        cells = table.add_row().cells
        for cell, text in zip(cells, [str(row.rule_id), str(row.username), str(row.severity), str(row.status), str(row.risk_score)]):
            cell.text = text
    docx_bytes = io.BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    pdf_bytes = io.BytesIO()
    pdf = SimpleDocTemplate(pdf_bytes, pagesize=landscape(A4), rightMargin=12 * mm, leftMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("CASO16 — Reporte ejecutivo de riesgos", styles["Title"]),
        Paragraph(f"Origen: Dataset público SharpHound/BloodHound AD · Emisor: {st.session_state.actor} · {generated}", styles["Normal"]),
        Spacer(1, 8),
    ]
    rows = [["Regla", "Cuenta", "Dominio", "Severidad", "Evidencia", "Estado", "Score"]]
    for _, row in findings.head(35).iterrows():
        rows.append([str(row.rule_id), str(row.username), str(row.source), str(row.severity), str(row.evidence_state), str(row.status), str(row.risk_score)])
    pdf_table = Table(rows, repeatRows=1)
    pdf_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2942")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(pdf_table)
    pdf.build(story)
    pdf_bytes.seek(0)

    dl1, dl2, dl3 = st.columns(3)
    with dl1:
        st.download_button("Descargar Excel (.xlsx)", data=xlsx.getvalue(), file_name="caso16_reporte.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", icon=":material/table_view:")
    with dl2:
        st.download_button("Descargar Word (.docx)", data=docx_bytes.getvalue(), file_name="caso16_reporte.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", icon=":material/article:")
    with dl3:
        st.download_button("Descargar PDF (.pdf)", data=pdf_bytes.getvalue(), file_name="caso16_reporte.pdf", mime="application/pdf", icon=":material/picture_as_pdf:")


def render_scan() -> None:
    st.title("Ejecución de detección", icon=":material/play_circle:")
    st.caption("Pipeline determinista: Dataset Público SharpHound/BloodHound AD → Reglas R01–R06 → Score 0–100 → Hallazgos → Bitácora.")
    with st.container(border=True):
        st.markdown("**Catálogo de reglas deterministas activas**")
        for rule_id, (name, description) in RULES.items():
            st.markdown(f"- **{rule_id} · {name}:** {description}")
        if st.button("Ejecutar escaneo determinista", type="primary", icon=":material/play_arrow:"):
            with st.status("Procesando 113 cuentas de Active Directory y evaluando reglas R01–R06…", expanded=False) as status_box:
                result = run_detection(st.session_state.actor, st.session_state.role)
                status_box.update(label="Escaneo completado exitosamente", state="complete")
            st.success(f"{result['accounts_processed']} cuentas procesadas · {result['findings_created']} hallazgos nuevos · corrida `{result['run_id']}`")
            st.rerun()
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

            if run_lf or "last_lf_output" not in st.session_state:
                st.session_state["last_lf_output"] = explain_finding_langflow(
                    int(selected_fid), actor=st.session_state.actor, role=st.session_state.role
                )

            lf_out = st.session_state.get("last_lf_output")
            if lf_out:
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
    st.title("Salud y arquitectura del sistema", icon=":material/health_and_safety:")
    health = api_health()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Estado API / Core", health.get("status", "unknown").upper(), border=True)
    c2.metric("Base de datos", health.get("database", "unknown"), border=True)
    c3.metric("Cuentas cargadas", health.get("accounts_loaded", 113), border=True)
    c4.metric("Orquestación", "n8n + LangFlow", border=True)
    st.dataframe(
        pd.DataFrame([
            {"Componente": "Persistencia", "Estado": health.get("database"), "Nota": "PostgreSQL 16 en Docker Compose / SQLite local sincronizado"},
            {"Componente": "Dataset Público AD", "Estado": "operativo (113 cuentas)", "Nota": "SharpHound/BloodHound: PHANTOM.CORP, WRAITH.CORP, GHOST.CORP, ESC1.LOCAL"},
            {"Componente": "Motor R01–R06", "Estado": "operativo (269 hallazgos)", "Nota": "Evaluación determinista auditable y score 0–100"},
            {"Componente": "Pipeline n8n", "Estado": "operativo (/api/v1/integrations/n8n/trigger)", "Nota": "Ejecución automatizada de 5 nodos y plantilla exportable JSON"},
            {"Componente": "Copiloto LangFlow IA", "Estado": "operativo (/api/v1/findings/{id}/explain)", "Nota": "Priorización, mapeo MITRE ATT&CK / ISO 27001 A.8.2 y remediación PowerShell"},
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
        st.title("CASO16 · SOC", icon=":material/security:")
        st.caption(f"👤 **{st.session_state.actor}**\n\n🛡️ {st.session_state.role}")
        page = st.radio(
            "Navegación",
            [
                "Dashboard",
                "Inventario",
                "Hallazgos",
                "n8n & LangFlow IA",
                "Auditoría",
                "Reportes",
                "Ejecutar escaneo",
                "Salud del sistema",
            ],
            label_visibility="collapsed",
        )
        st.space("small")
        if st.button("Cerrar sesión", icon=":material/logout:"):
            st.session_state.authenticated = False
            st.rerun()
        st.caption("v1.0 · SharpHound Public AD Dataset")
    if page == "Dashboard":
        render_dashboard()
    elif page == "Inventario":
        render_inventory()
    elif page == "Hallazgos":
        render_findings()
    elif page == "n8n & LangFlow IA":
        render_integrations()
    elif page == "Auditoría":
        render_audit()
    elif page == "Reportes":
        render_reports()
    elif page == "Ejecutar escaneo":
        render_scan()
    else:
        render_health()


main()
