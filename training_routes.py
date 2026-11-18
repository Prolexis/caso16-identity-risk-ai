"""Rutas REST de la API FastAPI para el Motor de Entrenamiento de Inteligencia Artificial (CASO16).

Provee endpoints para EDA, configuración de M1/M2/M3, ejecución con Optuna,
monitorización en tiempo real, cancelación segura, comparación de modelos y descarga de reportes.
"""
from __future__ import annotations

import json
from pathlib import Path
import threading
from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import data_layer as dl
from eda_engine import run_eda
from training_engine import (
    ExperimentConfig,
    MODEL_STORAGE_DIR,
    ModelParamsM1,
    ModelParamsM2,
    ModelParamsM3,
    TrainingPipelineEngine,
    generate_demo_dataset,
)
from training_reports import (
    export_experiment_excel,
    export_experiment_pdf,
    export_experiment_word,
)

training_router = APIRouter(prefix="/api/v1/training", tags=["Motor de Entrenamiento IA"])

# Estado de tareas en ejecución y tokens de cancelación
_active_jobs: dict[str, dict[str, Any]] = {}
_cancel_tokens: dict[str, threading.Event] = {}
_lock = threading.Lock()


class TrainStartRequest(BaseModel):
    run_m1: bool = Field(default=True, description="Entrenar M1 (Random Forest)")
    run_m2: bool = Field(default=True, description="Entrenar M2 (XGBoost)")
    run_m3: bool = Field(default=True, description="Entrenar M3 (Isolation Forest)")
    use_optuna: bool = Field(default=True, description="Habilitar optimización de hiperparámetros con Optuna")
    optuna_trials_m1: int = Field(default=15, ge=1, le=100)
    optuna_trials_m2: int = Field(default=15, ge=1, le=100)
    optuna_trials_m3: int = Field(default=10, ge=1, le=100)
    timeout_seconds: float = Field(default=180.0, ge=10.0, le=900.0)
    seed: int = Field(default=42)
    stratify: bool = Field(default=True)
    params_m1: dict[str, Any] = Field(default_factory=dict)
    params_m2: dict[str, Any] = Field(default_factory=dict)
    params_m3: dict[str, Any] = Field(default_factory=dict)
    use_demo_dataset: bool = Field(default=False, description="Usar dataset sintético de demostración")
    actor: str = Field(default="auditor@demo.local")


@training_router.get("/eda")
def get_eda(use_demo: bool = Query(default=False)) -> dict[str, Any]:
    """Ejecuta y retorna el Análisis Exploratorio de Datos (EDA) sobre las cuentas del inventario."""
    if use_demo:
        accounts = generate_demo_dataset(n=200)
    else:
        accounts = dl.account_frame().to_dict(orient="records")
        if not accounts:
            accounts = generate_demo_dataset(n=200)

    eda_result = run_eda(accounts)
    return eda_result


@training_router.get("/config/defaults")
def get_default_config() -> dict[str, Any]:
    """Retorna los parámetros predeterminados, rangos de Optuna y justificación técnica para M1, M2 y M3."""
    return {
        "m1_random_forest": {
            "name": "M1 — Random Forest Classifier",
            "type": "Supervisado (Clasificación de Severidad y Priorización)",
            "baseline": True,
            "defaults": {
                "n_estimators": 300,
                "max_depth": 12,
                "min_samples_leaf": 2,
                "min_samples_split": 4,
                "max_features": "sqrt",
                "class_weight": "balanced",
                "random_state": 42,
            },
            "optuna_search_space": {
                "n_estimators": [100, 600],
                "max_depth": [4, 24],
                "min_samples_leaf": [1, 10],
                "min_samples_split": [2, 20],
                "max_features": ["sqrt", "log2", 0.5, 0.8],
            },
            "stopping_condition": "Finalización de la cantidad de árboles o presupuesto de tiempo/trials. Sin early stopping clásico.",
            "rationale": "Ensamble no paramétrico robusto a outliers y no linealidades. Sirve de baseline sólido para la predicción de remediación.",
        },
        "m2_xgboost": {
            "name": "M2 — XGBoost Classifier",
            "type": "Supervisado (Boosting Gradiente Optimizado)",
            "baseline": False,
            "defaults": {
                "n_estimators": 500,
                "max_depth": 5,
                "learning_rate": 0.05,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
                "reg_lambda": 1.0,
                "early_stopping_rounds": 30,
                "random_state": 42,
            },
            "optuna_search_space": {
                "max_depth": [3, 10],
                "learning_rate": [0.01, 0.2],
                "subsample": [0.6, 1.0],
                "colsample_bytree": [0.6, 1.0],
                "reg_lambda": [0.001, 20.0],
            },
            "stopping_condition": "Detención temprana tras 30 rondas consecutivas sin mejora en validación, o número máximo de estimadores.",
            "rationale": "Modelo de gradient boosting con regularización L2. Maximiza la capacidad de separar casos críticos con calibración fina de probabilidades.",
        },
        "m3_isolation_forest": {
            "name": "M3 — Isolation Forest",
            "type": "No Supervisado (Detección de Anomalías de Cuentas)",
            "baseline": False,
            "defaults": {
                "n_estimators": 300,
                "max_samples": "auto",
                "contamination": "auto",
                "max_features": 1.0,
                "random_state": 42,
            },
            "optuna_search_space": {
                "n_estimators": [100, 500],
                "max_samples": [0.5, 1.0],
                "max_features": [0.5, 1.0],
            },
            "stopping_condition": "Construcción completa de los árboles de aislamiento o límite de memoria.",
            "rationale": "Aísla observaciones atípicas dividiendo aleatoriamente atributos. No requiere etiquetas previas y descubre comportamientos divergentes no contemplados en reglas estáticas.",
        },
    }


def _execute_training_job(job_id: str, rows: list[dict[str, Any]], exp_cfg: ExperimentConfig):
    cancel_evt = _cancel_tokens.get(job_id, threading.Event())

    def cancel_check() -> bool:
        return cancel_evt.is_set()

    def progress_cb(prog: dict[str, Any]):
        with _lock:
            if job_id in _active_jobs:
                _active_jobs[job_id]["progress"] = prog

    engine = TrainingPipelineEngine(cancel_token=cancel_check, progress_cb=progress_cb)

    try:
        result = engine.run_full_experiment(rows, exp_cfg)
        with _lock:
            if job_id in _active_jobs:
                _active_jobs[job_id]["status"] = "completed"
                _active_jobs[job_id]["result"] = result
                _active_jobs[job_id]["progress"]["percent"] = 100
                _active_jobs[job_id]["progress"]["message"] = "Entrenamiento completado exitosamente."
    except InterruptedError:
        with _lock:
            if job_id in _active_jobs:
                _active_jobs[job_id]["status"] = "cancelled"
                _active_jobs[job_id]["error"] = "El entrenamiento fue cancelado por el usuario."
    except Exception as exc:
        with _lock:
            if job_id in _active_jobs:
                _active_jobs[job_id]["status"] = "failed"
                _active_jobs[job_id]["error"] = f"{type(exc).__name__}: {str(exc)}"


@training_router.post("/start")
def start_training(payload: TrainStartRequest) -> dict[str, Any]:
    """Inicia un nuevo experimento de entrenamiento y optimización de hiperparámetros con Optuna."""
    job_id = f"job-{len(_active_jobs) + 1:03d}"

    if payload.use_demo_dataset:
        rows = generate_demo_dataset(n=220, seed=payload.seed)
    else:
        rows = dl.account_frame().to_dict(orient="records")
        if len(rows) < 15:
            rows = generate_demo_dataset(n=220, seed=payload.seed)

    exp_cfg = ExperimentConfig(
        run_m1=payload.run_m1,
        run_m2=payload.run_m2,
        run_m3=payload.run_m3,
        use_optuna=payload.use_optuna,
        optuna_trials_m1=payload.optuna_trials_m1,
        optuna_trials_m2=payload.optuna_trials_m2,
        optuna_trials_m3=payload.optuna_trials_m3,
        timeout_seconds=payload.timeout_seconds,
        seed=payload.seed,
        stratify=payload.stratify,
        params_m1=payload.params_m1,
        params_m2=payload.params_m2,
        params_m3=payload.params_m3,
    )

    with _lock:
        _cancel_tokens[job_id] = threading.Event()
        _active_jobs[job_id] = {
            "job_id": job_id,
            "status": "running",
            "actor": payload.actor,
            "created_at": str(dl.datetime.now(dl.timezone.utc)),
            "progress": {"stage": "init", "percent": 0, "message": "Iniciando pipeline de entrenamiento..."},
            "result": None,
            "error": None,
        }

    # Lanzar hilo desacoplado
    thread = threading.Thread(
        target=_execute_training_job,
        args=(job_id, rows, exp_cfg),
        daemon=True,
    )
    thread.start()

    return {"status": "started", "job_id": job_id, "message": "Entrenamiento iniciado en segundo plano."}


@training_router.get("/jobs")
def list_training_jobs() -> dict[str, Any]:
    """Lista todos los trabajos de entrenamiento y su estado."""
    # Consultar archivos persistidos en MODEL_STORAGE_DIR
    persisted_files = list(MODEL_STORAGE_DIR.glob("experiment_*.json"))
    items = []
    with _lock:
        for jid, job in _active_jobs.items():
            items.append({
                "job_id": jid,
                "status": job["status"],
                "actor": job.get("actor", "auditor@demo.local"),
                "progress": job.get("progress", {}),
                "created_at": job.get("created_at", ""),
                "has_result": job.get("result") is not None,
                "error": job.get("error"),
            })

    for p in sorted(persisted_files, key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                exp_id = data.get("experiment_id", p.stem)
                if not any(it["job_id"] == exp_id for it in items):
                    items.append({
                        "job_id": exp_id,
                        "status": data.get("status", "completed"),
                        "actor": "auditor@demo.local",
                        "progress": {"percent": 100, "message": "Completado"},
                        "created_at": data.get("completed_at", ""),
                        "has_result": True,
                        "error": None,
                    })
        except Exception:
            pass

    return {"jobs": items, "total": len(items)}


@training_router.get("/jobs/{job_id}")
def get_training_job(job_id: str) -> dict[str, Any]:
    """Consulta el estado detallado, métricas, progreso de Optuna y resultados de un trabajo."""
    with _lock:
        if job_id in _active_jobs:
            return _active_jobs[job_id]

    # Buscar en disco
    target_file = MODEL_STORAGE_DIR / f"experiment_{job_id}.json"
    if target_file.exists():
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "job_id": job_id,
                "status": data.get("status", "completed"),
                "progress": {"percent": 100, "message": "Completado"},
                "result": data,
                "error": None,
            }

    raise HTTPException(status_code=404, detail=f"Trabajo '{job_id}' no encontrado.")


@training_router.post("/jobs/{job_id}/cancel")
def cancel_training_job(job_id: str) -> dict[str, Any]:
    """Envía la señal de cancelación segura a un trabajo en ejecución."""
    with _lock:
        if job_id in _cancel_tokens:
            _cancel_tokens[job_id].set()
            if job_id in _active_jobs:
                _active_jobs[job_id]["status"] = "cancelling"
            return {"status": "cancelling", "job_id": job_id, "message": "Señal de parada enviada."}

    raise HTTPException(status_code=404, detail="El trabajo no se encuentra en ejecución activa.")


@training_router.get("/jobs/{job_id}/report")
def download_training_report(
    job_id: str,
    format: Literal["pdf", "docx", "xlsx"] = Query(default="pdf"),
    actor: str = Query(default="auditor@demo.local"),
):
    """Descarga el reporte técnico formal en formato PDF, Word (.docx) o Excel (.xlsx)."""
    # Obtener datos del experimento
    exp_data = None
    with _lock:
        if job_id in _active_jobs and _active_jobs[job_id].get("result"):
            exp_data = _active_jobs[job_id]["result"]

    if not exp_data:
        target_file = MODEL_STORAGE_DIR / f"experiment_{job_id}.json"
        if target_file.exists():
            with open(target_file, "r", encoding="utf-8") as f:
                exp_data = json.load(f)

    if not exp_data:
        raise HTTPException(status_code=404, detail=f"No hay resultados listos para generar el reporte de '{job_id}'.")

    if format == "xlsx":
        content = export_experiment_excel(exp_data, actor=actor)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"CASO16_Reporte_Entrenamiento_{job_id}.xlsx"
    elif format == "docx":
        content = export_experiment_word(exp_data, actor=actor)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = f"CASO16_Reporte_Entrenamiento_{job_id}.docx"
    else:
        content = export_experiment_pdf(exp_data, actor=actor)
        media_type = "application/pdf"
        filename = f"CASO16_Reporte_Entrenamiento_{job_id}.pdf"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
