"""Analyst views and authenticated HTTP boundary; no hidden ML computation."""
from __future__ import annotations
import os
import pandas as pd
import altair as alt
import requests
import streamlit as st
from reporting import descriptive_tables, dataset_hash


def api_request(method, path, payload=None):
    token = st.session_state.get("jwt_token")
    if not token:
        raise RuntimeError("Inicie sesión nuevamente para obtener un token válido.")
    try:
        response = requests.request(method, os.getenv("CASO16_API_URL", "http://127.0.0.1:8000/api/v1").rstrip("/") + path,
                                    json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=20)
        if not response.ok:
            raise RuntimeError(f"API {response.status_code}: {response.text[:500]}")
        return response.json() if response.content else {}
    except requests.RequestException as exc:
        raise RuntimeError("API no disponible; no se ejecutó una operación local alternativa.") from exc


def render_descriptive(accounts, findings):
    st.title("Datos · Estadística descriptiva")
    st.caption(f"Instantánea SHA-256: {dataset_hash(accounts)} · Fuente primaria: reglas R01–R06")
    if accounts.empty:
        st.info("Sin cuentas disponibles.")
        return
    domains = st.multiselect("Dominios", sorted(accounts.source.dropna().unique()), key="data_domains")
    selected = accounts[accounts.source.isin(domains)] if domains else accounts
    ff = findings[findings.account_id.isin(selected.id)] if "account_id" in findings else findings
    domain, rules = descriptive_tables(selected, ff)
    st.subheader("Resumen por dominio")
    st.dataframe(domain, hide_index=True)
    st.caption("La desviación resume heterogeneidad de scores; no representa incertidumbre predictiva.")
    if selected.empty:
        return
    hist = alt.Chart(selected).mark_bar().encode(x=alt.X("risk_score:Q", bin=alt.Bin(step=10), title="Score determinista (0–100)"), y=alt.Y("count():Q", title="Cuentas"), tooltip=["count():Q"]).properties(title="Distribución de score")
    st.altair_chart(hist)
    high = int(selected.risk_score.ge(60).sum())
    st.write(f"{high} de {len(selected)} cuentas ({high / len(selected):.1%}) tienen score ≥60; priorizar revisión de evidencia.")
    st.altair_chart(alt.Chart(selected).mark_boxplot().encode(x=alt.X("source:N", title="Dominio"), y=alt.Y("risk_score:Q", title="Score"), color="source:N").properties(title="Dispersión por dominio"))
    st.caption("Cajas anchas indican heterogeneidad, no necesariamente más incidentes confirmados.")
    heat = selected.copy()
    heat["categoría"] = pd.cut(heat.risk_score, [-1, 29, 59, 79, 100], labels=["0–29", "30–59", "60–79", "80–100"])
    st.altair_chart(alt.Chart(heat).mark_rect().encode(x=alt.X("categoría:N", title="Tramo descriptivo de score"), y=alt.Y("source:N", title="Dominio"), color=alt.Color("count():Q", title="Cuentas"), tooltip=["source:N", "categoría:N", "count():Q"]).properties(title="Concentración de cuentas por dominio y score"))
    st.caption("Los tramos son descriptivos; la severidad operacional se obtiene del motor y sus políticas.")
    st.subheader("Hallazgos por regla · Pareto")
    st.dataframe(rules, hide_index=True)
    if not rules.empty:
        st.bar_chart(rules, x="rule_id", y="n", x_label="Regla", y_label="Hallazgos")
        st.write(str(rules.iloc[0]["Interpretación"]))
    st.subheader("Evidencia de grupos R03 / R05")
    evidence = ff[ff.rule_id.isin(["R03", "R05"])] if "rule_id" in ff else pd.DataFrame()
    st.dataframe(evidence[[c for c in ["id", "rule_id", "username", "source", "evidence", "rationale"] if c in evidence]], hide_index=True)
    st.caption("Evidencia emitida por el motor: pertenencia o privilegio anómalo no demuestra por sí solo una intrusión.")


def render_metadata(accounts):
    st.subheader("Metadata de la cuenta")
    if st.session_state.role not in {"Superadministrador", "Administrador de seguridad"}:
        st.info("Solo administradores pueden editar metadata; la API vuelve a validar RBAC.")
        return
    if accounts.empty:
        return
    selected = st.selectbox("Cuenta para editar", accounts.id.tolist(), format_func=lambda i: f"#{i} · {accounts.loc[accounts.id == i, 'username'].iloc[0]}", key="metadata_account")
    row = accounts.loc[accounts.id == selected].iloc[0]
    with st.form("account_metadata"):
        verified = st.checkbox("Justificación de privilegio verificada", value=bool(row.get("justification_verified", False)))
        reason = st.text_area("Justificación de privilegio", value=str(row.get("privilege_justification", "") or ""))
        reviewed = st.checkbox("Registrar revisión hoy")
        if st.form_submit_button("Guardar metadata vía API"):
            from datetime import date
            payload = {"justification_verified": verified, "privilege_justification": reason}
            if reviewed:
                payload["review_at"] = date.today().isoformat()
            try:
                api_request("PATCH", f"/accounts/{selected}/metadata", payload)
                st.success("Metadata guardada y auditada. Actualice el inventario para ver el resultado.")
            except RuntimeError as exc:
                st.error(str(exc))
    st.caption("Las excepciones con vencimiento se administran en Políticas & Excepciones.")


def render_upload():
    with st.form("upload_accounts"):
        upload = st.file_uploader("Importar cuentas CSV / JSON", type=["csv", "json"])
        submit = st.form_submit_button("Validar e importar vía API")
    if submit:
        if upload is None:
            st.warning("Seleccione un archivo.")
        elif upload.size > 5 * 1024 * 1024:
            st.error("El archivo supera el límite de 5 MiB.")
        else:
            try:
                result = api_request("POST", "/accounts/import", {"content": upload.getvalue().decode("utf-8-sig"), "format": upload.name.rsplit(".", 1)[-1].lower()})
                st.json(result)
                st.caption("Revise las filas rechazadas y sus motivos antes de repetir la carga; el backend controla la idempotencia.")
            except (RuntimeError, UnicodeDecodeError) as exc:
                st.error(str(exc))


def render_evaluation():
    st.title("Evaluación registrada")
    st.warning("Etiquetas derivadas de reglas: el desempeño mide imitación del motor, no detección independiente de ataques.")
    try:
        items = api_request("GET", "/evaluation").get("items", [])
    except RuntimeError as exc:
        st.info(str(exc))
        return
    if not items:
        st.info("No hay evaluaciones completadas. No se generan curvas ni métricas simuladas.")
        return
    choice = st.selectbox("Evaluación", range(len(items)), format_func=lambda i: str(items[i].get("job_id", items[i].get("model_id", i))))
    result = items[choice]
    st.caption(f"Modelo: {result.get('model_id', 'no informado')} · Dataset: {result.get('dataset_hash', 'no informado')}")
    folds = result.get("folds", [])
    if folds:
        st.dataframe(pd.json_normalize(folds), hide_index=True)
        st.caption("Cada fold externo es una observación fuera de su ajuste interno. Variación entre folds no equivale a un IC del test.")
    for label, key in [("Agregación de folds", "aggregate"), ("Validación", "validation"), ("Prueba final", "test"), ("Intervalos bootstrap", "bootstrap")]:
        st.subheader(label)
        st.json(result.get(key, {}))
    st.write(result.get("interpretation", "Consulte métricas por clase y limitaciones de la partición."))
    st.caption("Grad-CAM no aplica a atributos tabulares. Solo se muestran explicaciones y métricas realmente persistidas.")


def render_inference(accounts):
    st.title("Inferencia · Reglas y segunda opinión")
    st.caption("El score determinista siempre es primario. Un modelo no disponible no se presenta como ML.")
    if accounts.empty:
        st.info("Sin cuentas para inferir.")
        return
    with st.form("predict_account"):
        account = st.selectbox("Cuenta", accounts.id.tolist(), format_func=lambda i: f"#{i} · {accounts.loc[accounts.id == i, 'username'].iloc[0]}")
        model = st.text_input("ID del modelo opcional", help="Vacío: fallback determinista; no entrena un modelo automáticamente.")
        submit = st.form_submit_button("Evaluar cuenta")
    if submit:
        try:
            result = api_request("POST", "/predict", {"account_id": int(account), "model_id": model or None})
            st.session_state["inference_result"] = result
            st.session_state["inference_account"] = int(account)
        except RuntimeError as exc:
            st.error(str(exc))
    result = st.session_state.get("inference_result")
    if result:
        st.caption(f"Resultado de cuenta #{st.session_state.get('inference_account')}; vuelva a evaluar después de cambiar el formulario.")
        st.metric("Score determinista", result.get("score", "N/D"))
        st.write(f"Severidad: {result.get('severity', 'N/D')} · Modo: {result.get('mode', 'no informado')}")
        if result.get("fallback_reason"):
            st.info(result["fallback_reason"])
        st.json(result)
        st.caption("Para crear un ticket auditable seleccione el hallazgo asociado en Hallazgos; no se crea un hallazgo ficticio desde la predicción.")
