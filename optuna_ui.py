"""Training and Optuna controls backed by persisted asynchronous API jobs."""
from __future__ import annotations
import json
import pandas as pd
import streamlit as st
from analytics_ui import api_request

MODELS = {"logistic": "Baseline lineal interpretable; limita relaciones no lineales.",
          "random_forest": "Árboles robustos a interacciones; controlar profundidad evita sobreajuste.",
          "gradient_boosting": "Boosting de árboles; tasa de aprendizaje regula cada corrección.",
          "mlp": "Red tabular ligera; puede ser inestable con pocas cuentas."}


def validate_search_space(text):
    space = json.loads(text)
    if not isinstance(space, dict):
        raise ValueError("El espacio debe ser un objeto JSON.")
    for name, spec in space.items():
        if not isinstance(spec, dict):
            raise ValueError(f"{name}: se requiere un objeto de rango o choices.")
        if "choices" in spec:
            if not isinstance(spec["choices"], list) or not spec["choices"]:
                raise ValueError(f"{name}: choices debe ser una lista no vacía.")
        elif "low" not in spec or "high" not in spec or spec["low"] > spec["high"]:
            raise ValueError(f"{name}: rango low/high inválido.")
        elif spec.get("log") and spec["low"] <= 0:
            raise ValueError(f"{name}: escala log requiere low > 0.")
    return space


@st.fragment(run_every="5s")
def monitor_job(job_id):
    try:
        job = api_request("GET", f"/train/{job_id}")
    except RuntimeError as exc:
        st.info(str(exc))
        return
    st.subheader(f"Job {job_id} · {job.get('status', 'desconocido')}")
    progress = job.get("progress") or {}
    st.json(progress)
    st.caption("Actualización cada 5 s. Solo se presentan valores reportados por el worker; no se inventa tiempo restante.")
    if job.get("error"):
        st.error(str(job["error"]))
    result = job.get("result")
    if result:
        if result.get("folds"):
            st.dataframe(pd.json_normalize(result["folds"]), hide_index=True)
        st.write(result.get("interpretation", "Trabajo completado; consulte Evaluación para resultados."))
        st.json(result.get("aggregate", {}))
    with st.expander("Registro completo del job"):
        st.json(job)


def render_training(optimization=False):
    st.title("Optimización Optuna" if optimization else "Entrenamiento supervisado")
    st.warning("ML es una segunda opinión experimental. Las etiquetas provienen de R01–R06: no constituyen verdad independiente de incidentes.")
    st.caption("CV anidada 5×3 por defecto; test reservado hasta evaluación final. Las particiones inviables deben fallar explícitamente, no degradarse silenciosamente.")
    with st.form("training_config"):
        model = st.selectbox("Modelo", list(MODELS), format_func=lambda m: {"logistic": "Regresión logística", "random_forest": "Random Forest", "gradient_boosting": "Gradient Boosting", "mlp": "MLP ligero"}[m])
        for key, rationale in MODELS.items():
            st.caption(f"{key}: {rationale}")
        trials = st.number_input("Trials por fold externo", min_value=1, max_value=200, value=50)
        seed = st.number_input("Semilla", min_value=0, max_value=2147483647, value=42)
        timeout = st.number_input("Timeout por estudio (segundos; 0 = sin límite)", min_value=0, max_value=86400, value=600)
        sampler = st.selectbox("Sampler", ["tpe", "random"], help="TPE aprende regiones prometedoras; Random proporciona una referencia sin modelo de búsqueda.")
        pruner = st.selectbox("Pruner", ["median", "hyperband", "none"], help="Solo poda si el objetivo reporta valores intermedios. No se promete ahorro cuando el estimador no los emite.")
        stratify = st.selectbox("Estratificación", ["joint", "severity"], help="joint: dominio × severidad. severity es una relajación explícita y debe quedar registrada.")
        space_text = st.text_area("Espacio de búsqueda JSON", value="{}", help='Ejemplo RF: {"n_estimators":{"low":100,"high":800},"max_depth":{"low":3,"high":12}}. Vacío usa rangos del backend.')
        st.caption("Más árboles aumentan coste; profundidad alta puede sobreajustar. learning_rate pequeño requiere más etapas. El backend valida parámetros compatibles con cada modelo.")
        start = st.form_submit_button("Iniciar CV anidada", type="primary")
    if start:
        try:
            config = {"model": model, "outer_folds": 5, "inner_folds": 3, "n_trials": int(trials), "seed": int(seed), "timeout": int(timeout) or None,
                      "sampler": sampler, "pruner": pruner, "stratify": stratify, "bootstrap_resamples": 1000, "search_space": validate_search_space(space_text)}
            job = api_request("POST", "/train", config)
            st.session_state["training_job_id"] = job["id"]
            st.session_state["last_training_config"] = config
            st.success("Job registrado. El worker ejecutará el entrenamiento, sin bloquear esta vista.")
        except (RuntimeError, ValueError, KeyError) as exc:
            st.error(str(exc))
    if optimization:
        st.subheader("Presets por usuario")
        with st.form("save_preset"):
            name = st.text_input("Nombre del preset")
            save = st.form_submit_button("Guardar última configuración enviada")
        if save:
            if not name.strip() or not st.session_state.get("last_training_config"):
                st.warning("Envíe una configuración válida y especifique un nombre.")
            else:
                try:
                    api_request("POST", "/presets", {"name": name.strip(), "config": st.session_state.last_training_config})
                    st.success("Preset guardado.")
                except RuntimeError as exc:
                    st.error(str(exc))
        if st.button("Consultar presets"):
            try:
                st.session_state["training_presets"] = api_request("GET", "/presets").get("items", [])
            except RuntimeError as exc:
                st.error(str(exc))
        presets = st.session_state.get("training_presets", [])
        if presets:
            index = st.selectbox("Preset", range(len(presets)), format_func=lambda i: presets[i]["name"])
            preset = presets[index]
            st.json(preset["config"])
            if st.button("Entrenar con preset seleccionado"):
                try:
                    st.session_state["training_job_id"] = api_request("POST", "/train", preset["config"])["id"]
                except RuntimeError as exc:
                    st.error(str(exc))
            if st.button("Eliminar preset seleccionado"):
                try:
                    api_request("DELETE", f"/presets/{preset['id']}")
                    st.session_state.pop("training_presets", None)
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))
    if st.button("Consultar historial de jobs"):
        try:
            st.session_state["training_jobs"] = api_request("GET", "/train").get("items", [])
        except RuntimeError as exc:
            st.error(str(exc))
    jobs = st.session_state.get("training_jobs", [])
    if jobs:
        selected = st.selectbox("Job histórico", [j["id"] for j in jobs])
        if st.button("Monitorear job seleccionado"):
            st.session_state["training_job_id"] = selected
    if st.session_state.get("training_job_id"):
        monitor_job(st.session_state.training_job_id)
    if optimization:
        st.info("No se dibujan convergencia, hiperimportancias ni Pareto sin trials persistidos disponibles. El progreso y los mejores parámetros por fold son los resultados reales del backend.")
