from __future__ import annotations

import io
from datetime import date, datetime, timezone

import pandas as pd
import streamlit as st

from data_layer import (
    RULES,
    account_frame,
    api_health,
    audit_frame,
    dashboard_metrics,
    finding_frame,
    init_db,
    run_detection,
    run_frame,
    update_finding,
)

st.set_page_config(page_title="CASO16 | SOC", page_icon=":material/security:", layout="wide")
init_db()

ROLES = {
    "analyst@demo.local": "Analista de ciberseguridad",
    "security@demo.local": "Administrador de seguridad",
    "auditor@demo.local": "Auditor",
}


def init_session() -> None:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("actor", "analyst@demo.local")
    st.session_state.setdefault("role", ROLES["analyst@demo.local"])


def login_view() -> None:
    st.title("CASO16")
    st.subheader("Centro de operaciones para identidades y privilegios")
    st.caption("Plataforma demostrable de detección determinista. No representa métricas de producción ni certificación ISO 27001.")
    with st.container(border=True):
        st.markdown("**Acceso de demostración**")
        actor = st.selectbox("Usuario", list(ROLES), format_func=lambda x: f"{x} · {ROLES[x]}")
        password = st.text_input("Contraseña", type="password", value="demo")
        if st.button("Iniciar sesión", type="primary", icon=":material/login:"):
            if password != "demo":
                st.error("Credenciales de demostración incorrectas.")
            else:
                st.session_state.authenticated = True
                st.session_state.actor = actor
                st.session_state.role = ROLES[actor]
                st.rerun()
    st.info("Credenciales sintéticas: cualquier usuario listado con contraseña **demo**.")


def severity_badge(value: str) -> str:
    colors = {"Crítico": "red", "Alto": "orange", "Medio": "blue", "Bajo": "green"}
    color = colors.get(value, "gray")
    return f":{color}-badge[{value}]"


def render_dashboard() -> None:
    st.title("Dashboard operacional", icon=":material/dashboard:")
    st.caption("Indicadores calculados sobre la corrida real del dataset público SharpHound / BloodHound Active Directory.")
    st.info("Dataset público cargado: Telemetría Active Directory SharpHound/BloodHound (113 cuentas únicas en dominios PHANTOM.CORP, WRAITH.CORP, GHOST.CORP y ESC1.LOCAL).", icon=":material/dataset:")
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
        ("Modo IA", "Determinista"),
    ]
    for col, (label, value) in zip(cols2, secondary):
        with col:
            st.metric(label, value, border=True)

    accounts = account_frame()
    findings = finding_frame()
    left, right = st.columns(2)
    with left:
        with st.container(border=True):
            st.subheader("Distribución de severidad", icon=":material/bar_chart:")
            if findings.empty:
                st.info("Aún no hay hallazgos. Ejecuta un escaneo determinista.")
            else:
                severity = findings.groupby("severity").size().rename("hallazgos").reindex(["Crítico", "Alto", "Medio", "Bajo"], fill_value=0)
                st.bar_chart(severity)
    with right:
        with st.container(border=True):
            st.subheader("Riesgo por cuenta", icon=":material/monitoring:")
            chart = accounts[["username", "risk_score"]].head(8).set_index("username")
            st.bar_chart(chart)
    with st.container(border=True):
        st.subheader("Hallazgos prioritarios", icon=":material/priority_high:")
        if findings.empty:
            st.caption("Sin datos todavía.")
        else:
            view = findings[["id", "rule_id", "username", "title", "severity", "evidence_state", "status", "risk_score"]].head(10).copy()
            st.dataframe(view, hide_index=True, width="stretch", column_config={"risk_score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100)})
    st.caption("La tendencia histórica requiere ejecuciones sucesivas; esta demo muestra el snapshot actual y no inventa series temporales.")


def render_inventory() -> None:
    st.title("Inventario de identidades", icon=":material/manage_accounts:")
    st.caption("Atributos expuestos por la fuente sintética. Las consultas reales AD/LDAP son de solo lectura y no están configuradas.")
    data = account_frame()
    c1, c2, c3 = st.columns(3)
    with c1:
        query = st.text_input("Buscar", placeholder="usuario, nombre o correo")
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
    cols = ["id", "username", "display_name", "email", "account_type", "source", "active", "is_admin", "privileged_roles", "last_activity", "review_at", "risk_score"]
    st.dataframe(data[cols], hide_index=True, width="stretch", column_config={"risk_score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100), "email": st.column_config.TextColumn("Correo", width="medium")})
    st.download_button("Exportar inventario CSV", data=data.to_csv(index=False).encode("utf-8"), file_name="caso16_inventario.csv", mime="text/csv", icon=":material/download:")


def render_findings() -> None:
    st.title("Hallazgos y remediación", icon=":material/assignment_late:")
    st.caption("Flujo trazable: Detectado → En evaluación → Asignado → En remediación → Pendiente de validación → Resuelto → Cerrado.")
    data = finding_frame()
    if data.empty:
        st.info("No hay hallazgos. Usa **Ejecutar escaneo** en el menú lateral.")
        return
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
    display = filtered[["id", "rule_id", "username", "title", "severity", "evidence_state", "status", "owner", "risk_score", "created_at"]]
    st.dataframe(display, hide_index=True, width="stretch", column_config={"risk_score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100)})
    if filtered.empty:
        return
    selected_id = st.selectbox("Selecciona un hallazgo para revisar", filtered["id"].tolist(), format_func=lambda x: f"#{x} · {filtered.loc[filtered.id == x, 'rule_id'].iloc[0]} · {filtered.loc[filtered.id == x, 'username'].iloc[0]}")
    finding = filtered[filtered["id"] == selected_id].iloc[0]
    with st.container(border=True):
        st.subheader(f"{finding['rule_id']} · {finding['title']}")
        st.markdown(f"**Cuenta:** `{finding['username']}` · **Severidad:** {severity_badge(finding['severity'])} · **Estado de evidencia:** `{finding['evidence_state']}`")
        st.write(finding["rationale"])
        st.code(finding["evidence"], language="text")
        with st.form(f"finding_form_{selected_id}"):
            new_status = st.selectbox("Nuevo estado", ["Detectado", "En evaluación", "Asignado", "En remediación", "Pendiente de validación", "Resuelto", "Cerrado", "Falso positivo", "Excepción"], index=["Detectado", "En evaluación", "Asignado", "En remediación", "Pendiente de validación", "Resuelto", "Cerrado", "Falso positivo", "Excepción"].index(finding["status"]) if finding["status"] in ["Detectado", "En evaluación", "Asignado", "En remediación", "Pendiente de validación", "Resuelto", "Cerrado", "Falso positivo", "Excepción"] else 0)
            owner = st.text_input("Responsable", value=finding["owner"] or "")
            comment = st.text_area("Comentario de revisión", placeholder="Documenta la decisión o evidencia adicional")
            if st.form_submit_button("Guardar actualización", type="primary", icon=":material/save:"):
                update_finding(int(selected_id), new_status, owner, st.session_state.actor, st.session_state.role, comment)
                st.success("Hallazgo actualizado y auditado.")
                st.rerun()


def render_audit() -> None:
    st.title("Bitácora de auditoría", icon=":material/history:")
    st.caption("Registros append-only generados por el backend de la demo; no contiene contraseñas ni tokens.")
    data = audit_frame()
    if data.empty:
        st.info("Aún no existen eventos.")
        return
    action = st.multiselect("Filtrar acciones", sorted(data["action"].unique()), default=[])
    if action:
        data = data[data["action"].isin(action)]
    st.dataframe(data, hide_index=True, width="stretch")
    st.download_button("Exportar bitácora CSV", data=data.to_csv(index=False).encode("utf-8"), file_name="caso16_auditoria.csv", mime="text/csv", icon=":material/download:")


def render_reports() -> None:
    st.title("Reportes trazables", icon=":material/description:")
    st.caption("Formatos generados desde los registros persistidos: Excel, Word y PDF. Origen: Dataset público SharpHound/BloodHound AD.")
    accounts = account_frame()
    findings = finding_frame()
    audit = audit_frame()
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    st.write(f"Emisor: **{st.session_state.actor}** · Generado: **{generated}**")
    if st.button("Registrar generación en bitácora", icon=":material/history:"):
        # A report event is written by a real scan/update path; this UI action is also persisted by the API layer.
        from data_layer import audit_event, engine
        with engine.begin() as conn:
            audit_event(conn, st.session_state.actor, st.session_state.role, "generate_report", "reports", "success", "Paquete de reportes solicitado desde la UI")
        st.success("Evento de generación registrado.")
    xlsx = io.BytesIO()
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        accounts.to_excel(writer, index=False, sheet_name="Inventario")
        findings.to_excel(writer, index=False, sheet_name="Hallazgos")
        audit.to_excel(writer, index=False, sheet_name="Auditoria")
    xlsx.seek(0)
    st.download_button("Descargar Excel", data=xlsx.getvalue(), file_name="caso16_reporte.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", icon=":material/table_view:")

    from docx import Document
    doc = Document()
    doc.add_heading("CASO16 — Reporte ejecutivo de riesgos", 0)
    doc.add_paragraph(f"Origen: Dataset público SharpHound/BloodHound AD (4 dominios) | Emisor: {st.session_state.actor} | Generado: {generated}")
    doc.add_heading("Resumen", level=1)
    m = dashboard_metrics()
    doc.add_paragraph(f"{m['accounts']} cuentas inventariadas, {m['open_findings']} hallazgos abiertos, riesgo acumulado {m['risk_total']}.")
    doc.add_heading("Hallazgos prioritarios", level=1)
    table = doc.add_table(rows=1, cols=5)
    for cell, text in zip(table.rows[0].cells, ["Regla", "Cuenta", "Severidad", "Estado", "Score"]): cell.text = text
    for _, row in findings.head(15).iterrows():
        cells = table.add_row().cells
        for cell, text in zip(cells, [row.rule_id, row.username, row.severity, row.status, str(row.risk_score)]): cell.text = text
    docx_bytes = io.BytesIO()
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    st.download_button("Descargar Word", data=docx_bytes.getvalue(), file_name="caso16_reporte.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", icon=":material/article:")

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    pdf_bytes = io.BytesIO()
    pdf = SimpleDocTemplate(pdf_bytes, pagesize=landscape(A4), rightMargin=12 * mm, leftMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    styles = getSampleStyleSheet()
    story = [Paragraph("CASO16 — Reporte ejecutivo de riesgos", styles["Title"]), Paragraph(f"Origen: Dataset público SharpHound/BloodHound AD · Emisor: {st.session_state.actor} · {generated}", styles["Normal"]), Spacer(1, 8)]
    rows = [["Regla", "Cuenta", "Severidad", "Evidencia", "Estado", "Score"]]
    for _, row in findings.head(25).iterrows(): rows.append([str(row.rule_id), str(row.username), str(row.severity), str(row.evidence_state), str(row.status), str(row.risk_score)])
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324f")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(table)
    pdf.build(story)
    pdf_bytes.seek(0)
    st.download_button("Descargar PDF", data=pdf_bytes.getvalue(), file_name="caso16_reporte.pdf", mime="application/pdf", icon=":material/picture_as_pdf:")


def render_scan() -> None:
    st.title("Ejecución de detección", icon=":material/play_circle:")
    st.caption("Flujo demo: fuente sintética → reglas R01–R06 → score explicable → hallazgos → bitácora. No ejecuta cambios en AD/LDAP.")
    with st.container(border=True):
        st.markdown("**Reglas activas**")
        for rule_id, (name, description) in RULES.items():
            st.markdown(f"- **{rule_id} · {name}:** {description}")
        if st.button("Ejecutar escaneo determinista", type="primary", icon=":material/play_arrow:"):
            with st.status("Procesando inventario y reglas…", expanded=False) as status_box:
                result = run_detection(st.session_state.actor, st.session_state.role)
                status_box.update(label="Escaneo completado", state="complete")
            st.success(f"{result['accounts_processed']} cuentas procesadas · {result['findings_created']} hallazgos nuevos · run `{result['run_id']}`")
            st.rerun()
    st.subheader("Historial de ejecuciones")
    history = run_frame()
    st.dataframe(history, hide_index=True, width="stretch")


def render_health() -> None:
    st.title("Salud y límites del sistema", icon=":material/health_and_safety:")
    health = api_health()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Backend demo", health.get("status", "unknown"), border=True)
    c2.metric("Base de datos", health.get("database", "unknown"), border=True)
    c3.metric("Modo IA", "determinista", border=True)
    c4.metric("Directorio", "sintético", border=True)
    st.dataframe(pd.DataFrame([
        {"Componente": "Persistencia", "Estado": health.get("database"), "Nota": "PostgreSQL si DATABASE_URL está configurada; SQLite fallback local explícito"},
        {"Componente": "Motor R01–R06", "Estado": "operativo", "Nota": "Reglas verificables y score 0–100"},
        {"Componente": "AD/LDAP", "Estado": "no configurado", "Nota": "No se inventa conectividad ni lastLogon real"},
        {"Componente": "LangFlow/LLM", "Estado": "no configurado", "Nota": "Se mantiene degradación determinista"},
        {"Componente": "n8n", "Estado": "no configurado", "Nota": "Flujo documentado, integración externa pendiente"},
    ]), hide_index=True, width="stretch")
    st.warning("Esta entrega es un MVP demostrable. SSO/OIDC, MFA, TLS productivo, rate limiting, conector LDAP real, LangFlow y n8n requieren configuración y validación externa.")


def main() -> None:
    init_session()
    if not st.session_state.authenticated:
        login_view()
        return
    with st.sidebar:
        st.title("CASO16", icon=":material/security:")
        st.caption(f"{st.session_state.actor}\n\n{st.session_state.role}")
        page = st.radio("Navegación", ["Dashboard", "Inventario", "Hallazgos", "Auditoría", "Reportes", "Ejecutar escaneo", "Salud del sistema"], label_visibility="collapsed")
        st.space("small")
        if st.button("Cerrar sesión", icon=":material/logout:"):
            st.session_state.authenticated = False
            st.rerun()
        st.caption("v0.1 · DEMO / datos sintéticos")
    if page == "Dashboard": render_dashboard()
    elif page == "Inventario": render_inventory()
    elif page == "Hallazgos": render_findings()
    elif page == "Auditoría": render_audit()
    elif page == "Reportes": render_reports()
    elif page == "Ejecutar escaneo": render_scan()
    else: render_health()


main()
