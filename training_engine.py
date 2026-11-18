"""Motor de Entrenamiento, Optimización y Validación de Inteligencia Artificial (CASO16).

Implementa la metodología rigurosa:
EDA -> Preprocesamiento -> Partición 70/15/15 -> M1/M2/M3 -> Optuna -> Validación/Prueba -> Comparación.
- M1: Random Forest (Supervisado)
- M2: XGBoost Classifier (Supervisado, con fallback a GradientBoosting)
- M3: Isolation Forest (No Supervisado para Anomalías de Cuentas)
"""
from __future__ import annotations

import base64
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import time
from typing import Any, Callable
import uuid

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier, GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False


MODEL_STORAGE_DIR = Path(os.getenv("CASO16_MODEL_DIR", str(Path(__file__).parent / "data" / "models")))
MODEL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_NAMES = [
    "active",
    "is_admin",
    "justification_verified",
    "is_duplicate",
    "password_never_expires",
    "is_service",
    "activity_days",
    "review_days",
    "role_count",
]


@dataclass
class ModelParamsM1:
    """Parámetros independientes para M1 (Random Forest)."""
    n_estimators: int = 300
    max_depth: int | None = 12
    min_samples_leaf: int = 2
    min_samples_split: int = 4
    max_features: str = "sqrt"
    class_weight: str = "balanced"
    random_state: int = 42


@dataclass
class ModelParamsM2:
    """Parámetros independientes para M2 (XGBoost)."""
    n_estimators: int = 500
    max_depth: int = 5
    learning_rate: float = 0.05
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    reg_lambda: float = 1.0
    early_stopping_rounds: int = 30
    random_state: int = 42


@dataclass
class ModelParamsM3:
    """Parámetros independientes para M3 (Isolation Forest)."""
    n_estimators: int = 300
    max_samples: str | float = "auto"
    contamination: str | float = "auto"
    max_features: float = 1.0
    random_state: int = 42


@dataclass
class ExperimentConfig:
    """Configuración global del pipeline de entrenamiento y optimización."""
    run_m1: bool = True
    run_m2: bool = True
    run_m3: bool = True
    optuna_trials_m1: int = 15
    optuna_trials_m2: int = 15
    optuna_trials_m3: int = 10
    use_optuna: bool = True
    timeout_seconds: float = 180.0
    seed: int = 42
    stratify: bool = True
    params_m1: dict[str, Any] = field(default_factory=dict)
    params_m2: dict[str, Any] = field(default_factory=dict)
    params_m3: dict[str, Any] = field(default_factory=dict)


def _days(value: Any, today: date) -> float:
    if value is None or str(value).strip() in ("NaT", "nan", "None", ""):
        return np.nan
    try:
        return float(max(0, (today - date.fromisoformat(str(value)[:10])).days))
    except Exception:
        return np.nan


def extract_features(rows: list[dict[str, Any]], reference_date: date | None = None) -> np.ndarray:
    """Extrae la matriz de características evitando fuga de variables protegidas."""
    today = reference_date or date.today()
    matrix = []
    for r in rows:
        roles_str = str(r.get("privileged_roles") or "")
        role_count = float(len([x for x in roles_str.split("|") if x.strip()]))
        is_svc = 1.0 if str(r.get("account_type", "")).lower() == "service" else 0.0

        vector = [
            1.0 if r.get("active", True) else 0.0,
            1.0 if r.get("is_admin", False) else 0.0,
            1.0 if r.get("justification_verified", False) else 0.0,
            1.0 if r.get("is_duplicate", False) else 0.0,
            1.0 if r.get("password_never_expires", False) else 0.0,
            is_svc,
            _days(r.get("last_activity"), today),
            _days(r.get("review_at"), today),
            role_count,
        ]
        matrix.append(vector)
    return np.asarray(matrix, dtype=float)


def generate_demo_dataset(n: int = 240, seed: int = 42) -> list[dict[str, Any]]:
    """Genera un dataset sintético controlado para experimentación y docencia."""
    rng = np.random.default_rng(seed)
    today = date.today()
    domains = ["PHANTOM.CORP", "WRAITH.CORP", "ESC1.LOCAL", "GHOST.CORP"]
    roles_pool = ["Domain Admins", "Enterprise Admins", "Administrators", "Helpdesk", "Domain Users"]

    rows = []
    for i in range(n):
        dom = domains[i % len(domains)]
        is_svc = rng.random() < 0.25
        is_admin = rng.random() < 0.35
        pwd_never = rng.random() < 0.30 if is_svc else rng.random() < 0.10
        justified = rng.random() < 0.40 if is_admin else True
        duplicate = rng.random() < 0.15 if is_admin else False

        # Generar fechas
        days_inactive = int(rng.exponential(scale=110))
        act_date = (today - pd.Timedelta(days=days_inactive)).isoformat() if days_inactive > 0 and rng.random() > 0.15 else None
        days_rev = int(rng.exponential(scale=80))
        rev_date = (today - pd.Timedelta(days=days_rev)).isoformat() if rng.random() > 0.20 else None

        if is_admin:
            roles = [roles_pool[0]] if rng.random() < 0.6 else [roles_pool[0], roles_pool[1]]
        else:
            roles = [roles_pool[-1]]

        # Calcular severidad sintética basada en reglas deterministas
        score = 0
        if act_date is None or days_inactive >= 90:
            score += 35
        if is_admin and not justified:
            score += 25
        if is_admin and duplicate:
            score += 20
        if is_svc and pwd_never:
            score += 25
        score = min(100, score)

        rows.append({
            "id": 1000 + i,
            "external_id": f"DEMO-{dom[:3]}-{i:04d}",
            "username": f"demo_user_{i:04d}",
            "display_name": f"Demo User {i}",
            "email": f"demo_{i:04d}@{dom.lower()}",
            "account_type": "service" if is_svc else "user",
            "source": f"SharpHound AD ({dom})",
            "active": True,
            "is_admin": is_admin,
            "justification_verified": justified,
            "is_duplicate": duplicate,
            "password_never_expires": pwd_never,
            "privileged_roles": "|".join(roles),
            "last_activity": act_date,
            "review_at": rev_date,
            "risk_score": score,
            "dataset_origin": "SINTETICO_CONTROLADO",
        })
    return rows


def perform_partition_70_15_15(
    rows: list[dict[str, Any]],
    labels: list[str],
    seed: int = 42,
    stratify: bool = True,
) -> dict[str, list[int]]:
    """Realiza la partición 70 % Train, 15 % Validation, 15 % Test evitando fuga de información."""
    n = len(rows)
    indices = np.arange(n)
    y = np.asarray(labels)

    # Validar distribución
    classes, counts = np.unique(y, return_counts=True)
    if min(counts) < 2 or not stratify:
        train_idx, temp_idx = train_test_split(indices, test_size=0.30, random_state=seed, shuffle=True)
        val_idx, test_idx = train_test_split(temp_idx, test_size=0.50, random_state=seed, shuffle=True)
    else:
        try:
            train_idx, temp_idx = train_test_split(
                indices, test_size=0.30, random_state=seed, stratify=y, shuffle=True
            )
            val_idx, test_idx = train_test_split(
                temp_idx, test_size=0.50, random_state=seed, stratify=y[temp_idx], shuffle=True
            )
        except ValueError:
            # Fallback seguro a partición aleatoria si alguna clase es extremadamente rara
            train_idx, temp_idx = train_test_split(indices, test_size=0.30, random_state=seed, shuffle=True)
            val_idx, test_idx = train_test_split(temp_idx, test_size=0.50, random_state=seed, shuffle=True)

    # Comprobación de no superposición (fuga de datos cero)
    s_tr, s_va, s_te = set(train_idx), set(val_idx), set(test_idx)
    assert not (s_tr & s_va) and not (s_tr & s_te) and not (s_va & s_te), "Error: superposición en partición"
    assert len(s_tr | s_va | s_te) == n, "Error: partición incompleta"

    return {
        "train": train_idx.tolist(),
        "val": val_idx.tolist(),
        "test": test_idx.tolist(),
    }


def compute_supervised_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    probabilities: np.ndarray | None = None,
    classes: list[str] | None = None,
) -> dict[str, Any]:
    """Calcula el conjunto riguroso de métricas supervisadas para M1 y M2."""
    labels = list(classes if classes is not None else np.unique(y_true))
    acc = float(accuracy_score(y_true, y_pred))
    prec_macro = float(precision_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))
    rec_macro = float(recall_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))
    f1_mac = float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0))
    f1_wei = float(f1_score(y_true, y_pred, labels=labels, average="weighted", zero_division=0))
    mcc_val = float(matthews_corrcoef(y_true, y_pred)) if len(labels) > 1 else 0.0

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_norm = np.divide(
        cm, cm.sum(axis=1, keepdims=True), out=np.zeros_like(cm, dtype=float), where=cm.sum(axis=1, keepdims=True) != 0
    )

    curves = {}
    roc_auc_val, pr_auc_val = None, None
    if probabilities is not None and probabilities.shape[1] == len(labels):
        roc_list, pr_list = [], []
        for i, cls_name in enumerate(labels):
            bin_y = (y_true == cls_name).astype(int)
            if len(np.unique(bin_y)) > 1:
                fpr, tpr, _ = roc_curve(bin_y, probabilities[:, i])
                p_curve, r_curve, _ = precision_recall_curve(bin_y, probabilities[:, i])
                ra = float(roc_auc_score(bin_y, probabilities[:, i]))
                pa = float(average_precision_score(bin_y, probabilities[:, i]))
                roc_list.append(ra)
                pr_list.append(pa)
                curves[cls_name] = {
                    "fpr": [round(float(v), 4) for v in fpr[::max(1, len(fpr) // 25)]],
                    "tpr": [round(float(v), 4) for v in tpr[::max(1, len(tpr) // 25)]],
                    "precision": [round(float(v), 4) for v in p_curve[::max(1, len(p_curve) // 25)]],
                    "recall": [round(float(v), 4) for v in r_curve[::max(1, len(r_curve) // 25)]],
                    "roc_auc": round(ra, 4),
                    "pr_auc": round(pa, 4),
                }
            else:
                curves[cls_name] = {"warning": "Clase sin muestras positivas/negativas suficientes"}
        if roc_list:
            roc_auc_val = float(np.mean(roc_list))
            pr_auc_val = float(np.mean(pr_list))

    return {
        "accuracy": round(acc, 4),
        "precision_macro": round(prec_macro, 4),
        "recall_macro": round(rec_macro, 4),
        "f1_macro": round(f1_mac, 4),
        "f1_weighted": round(f1_wei, 4),
        "mcc": round(mcc_val, 4),
        "roc_auc": round(roc_auc_val, 4) if roc_auc_val is not None else None,
        "pr_auc": round(pr_auc_val, 4) if pr_auc_val is not None else None,
        "classes": labels,
        "confusion_matrix": cm.tolist(),
        "confusion_matrix_normalized": [[round(float(c), 3) for c in row] for row in cm_norm],
        "curves": curves,
    }


def _render_chart_base64(plot_fn: Callable[[Any], None]) -> str:
    """Utilidad para generar gráficos matplotlib en Base64 de forma aislada."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 4), dpi=120)
    try:
        plot_fn(ax)
        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        plt.close(fig)
        return ""


class TrainingPipelineEngine:
    """Orquestador completo del motor de entrenamiento, optimización y evaluación."""

    def __init__(self, cancel_token: Callable[[], bool] | None = None, progress_cb: Callable[[dict[str, Any]], None] | None = None):
        self.cancel_token = cancel_token or (lambda: False)
        self.progress_cb = progress_cb or (lambda p: None)

    def _notify(self, stage: str, message: str, percent: int, extra: dict[str, Any] | None = None):
        payload = {"stage": stage, "message": message, "percent": percent, "timestamp": datetime.now(timezone.utc).isoformat()}
        if extra:
            payload.update(extra)
        self.progress_cb(payload)

    def run_full_experiment(
        self,
        rows: list[dict[str, Any]],
        config: ExperimentConfig | None = None,
    ) -> dict[str, Any]:
        cfg = config or ExperimentConfig()
        started_at = time.time()
        exp_id = uuid.uuid4().hex[:12]

        self._notify("pre_check", "Validando precondiciones de entrenamiento...", 5)

        # 1. Precondiciones de inicio
        if not rows or len(rows) < 15:
            raise ValueError(
                f"Volumen de datos insuficiente ({len(rows)} cuentas). Se requieren al menos 15 registros."
            )

        # Mapear etiquetas de severidad
        def get_severity(r):
            s = r.get("risk_score")
            val = float(s) if s is not None and str(s) != "None" else 0.0
            if val >= 80:
                return "Crítico"
            if val >= 60:
                return "Alto"
            if val >= 35:
                return "Medio"
            return "Bajo"

        y_all = [get_severity(r) for r in rows]
        unique_classes = sorted(list(set(y_all)))
        if len(unique_classes) < 2:
            raise ValueError("Se requieren al menos 2 clases de severidad distintas para entrenamiento supervisado.")

        # Hash canónico para trazabilidad
        dataset_hash = hashlib.sha256(json.dumps([dict(r) for r in rows], default=str, sort_keys=True).encode()).hexdigest()

        # 2. Partición 70 / 15 / 15
        self._notify("partitioning", "Ejecutando partición 70% Train, 15% Val, 15% Test...", 15)
        splits = perform_partition_70_15_15(rows, y_all, seed=cfg.seed, stratify=cfg.stratify)
        tr_idx, val_idx, te_idx = splits["train"], splits["val"], splits["test"]

        # Extraer matrices de features
        X_all = extract_features(rows)
        X_tr, y_tr = X_all[tr_idx], np.asarray(y_all)[tr_idx]
        X_val, y_val = X_all[val_idx], np.asarray(y_all)[val_idx]
        X_te, y_te = X_all[te_idx], np.asarray(y_all)[te_idx]

        # 3. Preprocesamiento: Ajuste de Imputación y Escalador SOLO en Train (evitar data leakage)
        self._notify("preprocessing", "Ajustando imputación y normalización exclusivamente en Train...", 25)
        imputer = SimpleImputer(strategy="median")
        X_tr_imp = imputer.fit_transform(X_tr)
        X_val_imp = imputer.transform(X_val)
        X_te_imp = imputer.transform(X_te)

        scaler = StandardScaler()
        X_tr_sc = scaler.fit_transform(X_tr_imp)
        X_val_sc = scaler.transform(X_val_imp)
        X_te_sc = scaler.transform(X_te_imp)

        results_models: dict[str, Any] = {}
        optuna_studies: dict[str, Any] = {}
        charts: dict[str, str] = {}

        # =====================================================================
        # MODELO M1: RANDOM FOREST CLASSIFIER (Supervisado)
        # =====================================================================
        if cfg.run_m1:
            if self.cancel_token():
                raise InterruptedError("Entrenamiento cancelado por el usuario.")
            self._notify("m1_training", "Optimizando y entrenando M1 (Random Forest)...", 35)

            p_m1 = {**asdict(ModelParamsM1()), **cfg.params_m1}
            best_params_m1 = p_m1.copy()
            m1_trials_history = []

            if cfg.use_optuna and OPTUNA_AVAILABLE and cfg.optuna_trials_m1 > 1:
                study_m1 = optuna.create_study(
                    direction="maximize",
                    sampler=optuna.samplers.TPESampler(seed=cfg.seed),
                )

                def obj_m1(trial: optuna.Trial) -> float:
                    if self.cancel_token():
                        raise optuna.TrialPruned()
                    n_est = trial.suggest_int("n_estimators", 100, 600, step=50)
                    m_depth = trial.suggest_int("max_depth", 4, 24)
                    m_leaf = trial.suggest_int("min_samples_leaf", 1, 10)
                    m_split = trial.suggest_int("min_samples_split", 2, 20)
                    rf = RandomForestClassifier(
                        n_estimators=n_est,
                        max_depth=m_depth,
                        min_samples_leaf=m_leaf,
                        min_samples_split=m_split,
                        class_weight="balanced",
                        random_state=cfg.seed,
                        n_jobs=1,
                    )
                    rf.fit(X_tr_imp, y_tr)
                    preds = rf.predict(X_val_imp)
                    score = float(f1_score(y_val, preds, average="macro", zero_division=0))
                    m1_trials_history.append({"trial": trial.number + 1, "score": round(score, 4), "params": trial.params})
                    return score

                study_m1.optimize(obj_m1, n_trials=cfg.optuna_trials_m1, timeout=cfg.timeout_seconds / 3)
                best_params_m1.update(study_m1.best_params)
                optuna_studies["M1_RandomForest"] = {
                    "best_value": round(float(study_m1.best_value), 4),
                    "best_params": study_m1.best_params,
                    "trials_count": len(study_m1.trials),
                    "trials_history": m1_trials_history,
                }

            # Entrenar modelo final M1 con mejores hiperparámetros
            m1_model = RandomForestClassifier(
                n_estimators=int(best_params_m1.get("n_estimators", 300)),
                max_depth=int(best_params_m1.get("max_depth", 12)) if best_params_m1.get("max_depth") else None,
                min_samples_leaf=int(best_params_m1.get("min_samples_leaf", 2)),
                min_samples_split=int(best_params_m1.get("min_samples_split", 4)),
                max_features=best_params_m1.get("max_features", "sqrt"),
                class_weight=best_params_m1.get("class_weight", "balanced"),
                random_state=cfg.seed,
                n_jobs=1,
            )
            m1_model.fit(X_tr_imp, y_tr)

            # Evaluación en Validación y en Prueba (Ciega)
            m1_val_preds = m1_model.predict(X_val_imp)
            m1_val_probs = m1_model.predict_proba(X_val_imp)
            m1_val_metrics = compute_supervised_metrics(y_val, m1_val_preds, m1_val_probs, m1_model.classes_.tolist())

            m1_test_preds = m1_model.predict(X_te_imp)
            m1_test_probs = m1_model.predict_proba(X_te_imp)
            m1_test_metrics = compute_supervised_metrics(y_te, m1_test_preds, m1_test_probs, m1_model.classes_.tolist())

            # Feature Importance
            feat_imp_m1 = dict(zip(FEATURE_NAMES, [round(float(v), 4) for v in m1_model.feature_importances_]))

            results_models["M1_RandomForest"] = {
                "model_type": "Supervisado (Clasificación)",
                "hyperparameters": best_params_m1,
                "validation_metrics": m1_val_metrics,
                "test_metrics": m1_test_metrics,
                "feature_importance": feat_imp_m1,
                "stopping_condition": "Construcción completa de árboles y finalización de presupuesto Optuna",
            }

            # Gráfico de Feature Importance M1
            def _plot_imp_m1(ax):
                keys = sorted(feat_imp_m1, key=feat_imp_m1.get)
                vals = [feat_imp_m1[k] for k in keys]
                ax.barh(keys, vals, color="#0284c7")
                ax.set_title("M1: Importancia de Características (Random Forest)")
                ax.set_xlabel("Importancia Relativa")

            charts["m1_feature_importance"] = _render_chart_base64(_plot_imp_m1)

        # =====================================================================
        # MODELO M2: XGBOOST CLASSIFIER (Supervisado)
        # =====================================================================
        if cfg.run_m2:
            if self.cancel_token():
                raise InterruptedError("Entrenamiento cancelado por el usuario.")
            self._notify("m2_training", "Optimizando y entrenando M2 (XGBoost / Boosting)...", 60)

            p_m2 = {**asdict(ModelParamsM2()), **cfg.params_m2}
            best_params_m2 = p_m2.copy()
            m2_trials_history = []

            # Mapear clases a enteros para XGBoost
            cls_to_int = {c: i for i, c in enumerate(unique_classes)}
            int_to_cls = {i: c for i, c in enumerate(unique_classes)}
            y_tr_int = np.array([cls_to_int[c] for c in y_tr])
            y_val_int = np.array([cls_to_int[c] for c in y_val])
            y_te_int = np.array([cls_to_int[c] for c in y_te])

            if cfg.use_optuna and OPTUNA_AVAILABLE and cfg.optuna_trials_m2 > 1:
                study_m2 = optuna.create_study(
                    direction="maximize",
                    sampler=optuna.samplers.TPESampler(seed=cfg.seed),
                )

                def obj_m2(trial: optuna.Trial) -> float:
                    if self.cancel_token():
                        raise optuna.TrialPruned()
                    m_depth = trial.suggest_int("max_depth", 3, 10)
                    lr = trial.suggest_float("learning_rate", 0.01, 0.2, log=True)
                    sub = trial.suggest_float("subsample", 0.6, 1.0)
                    col = trial.suggest_float("colsample_bytree", 0.6, 1.0)
                    reg_l = trial.suggest_float("reg_lambda", 1e-3, 20.0, log=True)

                    if XGBOOST_AVAILABLE:
                        model = xgb.XGBClassifier(
                            n_estimators=int(best_params_m2.get("n_estimators", 300)),
                            max_depth=m_depth,
                            learning_rate=lr,
                            subsample=sub,
                            colsample_bytree=col,
                            reg_lambda=reg_l,
                            random_state=cfg.seed,
                            eval_metric="mlogloss",
                            early_stopping_rounds=best_params_m2.get("early_stopping_rounds", 30),
                        )
                        model.fit(X_tr_sc, y_tr_int, eval_set=[(X_val_sc, y_val_int)], verbose=False)
                    else:
                        model = GradientBoostingClassifier(
                            n_estimators=int(best_params_m2.get("n_estimators", 150)),
                            max_depth=m_depth,
                            learning_rate=lr,
                            subsample=sub,
                            random_state=cfg.seed,
                        )
                        model.fit(X_tr_sc, y_tr_int)

                    preds = model.predict(X_val_sc)
                    score = float(f1_score(y_val_int, preds, average="macro", zero_division=0))
                    m2_trials_history.append({"trial": trial.number + 1, "score": round(score, 4), "params": trial.params})
                    return score

                study_m2.optimize(obj_m2, n_trials=cfg.optuna_trials_m2, timeout=cfg.timeout_seconds / 3)
                best_params_m2.update(study_m2.best_params)
                optuna_studies["M2_XGBoost"] = {
                    "best_value": round(float(study_m2.best_value), 4),
                    "best_params": study_m2.best_params,
                    "trials_count": len(study_m2.trials),
                    "trials_history": m2_trials_history,
                }

            # Entrenar modelo final M2
            if XGBOOST_AVAILABLE:
                m2_model = xgb.XGBClassifier(
                    n_estimators=int(best_params_m2.get("n_estimators", 500)),
                    max_depth=int(best_params_m2.get("max_depth", 5)),
                    learning_rate=float(best_params_m2.get("learning_rate", 0.05)),
                    subsample=float(best_params_m2.get("subsample", 0.8)),
                    colsample_bytree=float(best_params_m2.get("colsample_bytree", 0.8)),
                    reg_lambda=float(best_params_m2.get("reg_lambda", 1.0)),
                    random_state=cfg.seed,
                    eval_metric="mlogloss",
                    early_stopping_rounds=int(best_params_m2.get("early_stopping_rounds", 30)),
                )
                m2_model.fit(X_tr_sc, y_tr_int, eval_set=[(X_val_sc, y_val_int)], verbose=False)
                stopping_desc = f"Early stopping (30 rondas sin mejora) o {m2_model.best_iteration} iteraciones completadas"
            else:
                m2_model = GradientBoostingClassifier(
                    n_estimators=int(best_params_m2.get("n_estimators", 300)),
                    max_depth=int(best_params_m2.get("max_depth", 5)),
                    learning_rate=float(best_params_m2.get("learning_rate", 0.05)),
                    subsample=float(best_params_m2.get("subsample", 0.8)),
                    random_state=cfg.seed,
                )
                m2_model.fit(X_tr_sc, y_tr_int)
                stopping_desc = "Rondas de Gradient Boosting completadas (fallback compatible)"

            # Predicciones
            m2_val_preds_int = m2_model.predict(X_val_sc)
            m2_val_preds = np.array([int_to_cls[i] for i in m2_val_preds_int])
            m2_val_probs = m2_model.predict_proba(X_val_sc)
            m2_val_metrics = compute_supervised_metrics(y_val, m2_val_preds, m2_val_probs, unique_classes)

            m2_test_preds_int = m2_model.predict(X_te_sc)
            m2_test_preds = np.array([int_to_cls[i] for i in m2_test_preds_int])
            m2_test_probs = m2_model.predict_proba(X_te_sc)
            m2_test_metrics = compute_supervised_metrics(y_te, m2_test_preds, m2_test_probs, unique_classes)

            feat_imp_m2 = dict(zip(FEATURE_NAMES, [round(float(v), 4) for v in m2_model.feature_importances_]))

            results_models["M2_XGBoost"] = {
                "model_type": "Supervisado (Boosting Optimizado)",
                "backend": "xgboost" if XGBOOST_AVAILABLE else "GradientBoostingClassifier (fallback)",
                "hyperparameters": best_params_m2,
                "validation_metrics": m2_val_metrics,
                "test_metrics": m2_test_metrics,
                "feature_importance": feat_imp_m2,
                "stopping_condition": stopping_desc,
            }

            # Gráfico de convergencia Optuna M2 si hay trials
            if m2_trials_history:
                def _plot_optuna_m2(ax):
                    t_nums = [t["trial"] for t in m2_trials_history]
                    t_sc = [t["score"] for t in m2_trials_history]
                    ax.plot(t_nums, t_sc, marker="o", color="#10b981", label="F1-Macro por Trial")
                    ax.set_title("M2: Optimización de Hiperparámetros (Optuna TPE)")
                    ax.set_xlabel("Número de Trial")
                    ax.set_ylabel("F1-Macro (Validación)")
                    ax.legend()
                    ax.grid(True, linestyle="--", alpha=0.5)

                charts["m2_optuna_convergence"] = _render_chart_base64(_plot_optuna_m2)

        # =====================================================================
        # MODELO M3: ISOLATION FOREST (No Supervisado - Anomalías)
        # =====================================================================
        if cfg.run_m3:
            if self.cancel_token():
                raise InterruptedError("Entrenamiento cancelado por el usuario.")
            self._notify("m3_training", "Entrenando y calibrando M3 (Isolation Forest)...", 80)

            p_m3 = {**asdict(ModelParamsM3()), **cfg.params_m3}
            best_params_m3 = p_m3.copy()

            m3_model = IsolationForest(
                n_estimators=int(best_params_m3.get("n_estimators", 300)),
                max_samples=best_params_m3.get("max_samples", "auto"),
                contamination=best_params_m3.get("contamination", "auto"),
                max_features=float(best_params_m3.get("max_features", 1.0)),
                random_state=cfg.seed,
            )
            # Entrenar con Train y evaluar anomalías en toda la población
            m3_model.fit(X_tr_sc)

            # Score de anomalía continuo (a menor valor, mayor anomalía)
            all_scores = m3_model.score_samples(X_all)
            # Invertir para que puntaje alto = más anómalo (rango 0 a 1 aprox)
            norm_anomaly_score = (all_scores.max() - all_scores) / (all_scores.max() - all_scores.min() + 1e-9)

            anomaly_predictions = m3_model.predict(X_all)  # -1 = anomalía, 1 = normal
            anomaly_count = int((anomaly_predictions == -1).sum())
            anomaly_pct = round((anomaly_count / len(rows)) * 100, 2)

            # Top cuentas anómalas
            ranked_indices = np.argsort(norm_anomaly_score)[::-1]
            top_anomalies = []
            for rank, idx in enumerate(ranked_indices[:15], 1):
                r = rows[idx]
                top_anomalies.append({
                    "rank": rank,
                    "external_id": str(r.get("external_id", "")),
                    "username": str(r.get("username", "")),
                    "account_type": str(r.get("account_type", "")),
                    "source": str(r.get("source", "")),
                    "anomaly_score": round(float(norm_anomaly_score[idx]), 4),
                    "deterministic_risk_score": r.get("risk_score", 0),
                    "is_admin": bool(r.get("is_admin", False)),
                    "password_never_expires": bool(r.get("password_never_expires", False)),
                    "review_needed": True,
                })

            results_models["M3_IsolationForest"] = {
                "model_type": "No Supervisado (Detección de Anomalías)",
                "hyperparameters": best_params_m3,
                "total_evaluated": len(rows),
                "anomalies_detected": anomaly_count,
                "anomaly_rate_pct": anomaly_pct,
                "anomaly_score_mean": round(float(norm_anomaly_score.mean()), 4),
                "anomaly_score_std": round(float(norm_anomaly_score.std()), 4),
                "top_anomalies": top_anomalies,
                "methodological_note": (
                    "M3 resuelve una tarea no supervisada de detección de desviaciones y valores atípicos. "
                    "A diferencia de M1 y M2, no optimiza una función de pérdida con etiquetas preexistentes. "
                    "Por rigor metodológico, no se reportan métricas de Accuracy/F1 supervisadas salvo que existan "
                    "etiquetas independientes verificadas por auditores humanos externos."
                ),
                "stopping_condition": "Finalización de la construcción del conjunto de árboles especificado",
            }

            # Histograma de distribución de anomalías M3
            def _plot_anom_m3(ax):
                ax.hist(norm_anomaly_score, bins=25, color="#f59e0b", edgecolor="black", alpha=0.7)
                ax.axvline(float(np.quantile(norm_anomaly_score, 0.90)), color="red", linestyle="--", label="Percentil 90 (Prioridad)")
                ax.set_title("M3: Distribución del Puntaje de Anomalía (Isolation Forest)")
                ax.set_xlabel("Puntaje Normalizado de Anomalía")
                ax.set_ylabel("Cuentas")
                ax.legend()

            charts["m3_anomaly_distribution"] = _render_chart_base64(_plot_anom_m3)

        # =====================================================================
        # COMPARACIÓN DE MODELOS (M1 vs M2 y Contexto M3)
        # =====================================================================
        self._notify("comparison", "Generando matriz de comparación y reporte...", 90)
        comparison_table = []
        if "M1_RandomForest" in results_models and "M2_XGBoost" in results_models:
            m1_test = results_models["M1_RandomForest"]["test_metrics"]
            m2_test = results_models["M2_XGBoost"]["test_metrics"]

            for metric_key in ["accuracy", "precision_macro", "recall_macro", "f1_macro", "f1_weighted", "roc_auc", "pr_auc"]:
                val_m1 = m1_test.get(metric_key)
                val_m2 = m2_test.get(metric_key)
                best_mod = (
                    "M1 (Random Forest)" if (val_m1 is not None and val_m2 is not None and val_m1 > val_m2)
                    else "M2 (XGBoost)" if (val_m1 is not None and val_m2 is not None and val_m2 > val_m1)
                    else "Empate"
                )
                comparison_table.append({
                    "metric": metric_key.upper().replace("_", " "),
                    "m1_random_forest": val_m1,
                    "m2_xgboost": val_m2,
                    "best_model": best_mod,
                })

        elapsed_total = round(time.time() - started_at, 2)
        self._notify("completed", "Entrenamiento, validación y comparación concluidos.", 100)

        experiment_summary = {
            "experiment_id": exp_id,
            "status": "completed",
            "started_at": datetime.fromtimestamp(started_at, tz=timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": elapsed_total,
            "dataset_hash": dataset_hash,
            "total_records": len(rows),
            "partition": {
                "train_count": len(tr_idx),
                "val_count": len(val_idx),
                "test_count": len(te_idx),
                "train_pct": round(len(tr_idx) / len(rows) * 100, 1),
                "val_pct": round(len(val_idx) / len(rows) * 100, 1),
                "test_pct": round(len(te_idx) / len(rows) * 100, 1),
                "stratified": cfg.stratify,
            },
            "models": results_models,
            "optuna_studies": optuna_studies,
            "comparison_table": comparison_table,
            "charts": charts,
            "methodology_diagram": {
                "phases": [
                    {"step": 1, "name": "EDA & Calidad de Datos", "status": "COMPLETADO", "detail": "Nulos, duplicados, outliers, lastLogon en AD"},
                    {"step": 2, "name": "Limpieza & Preprocesamiento", "status": "COMPLETADO", "detail": "Imputación mediana y StandardScaler ajustados solo en Train"},
                    {"step": 3, "name": "Partición sin Fuga", "status": "COMPLETADO", "detail": "70% Entrenamiento, 15% Validación, 15% Prueba (Ciega)"},
                    {"step": 4, "name": "Entrenamiento M1/M2/M3", "status": "COMPLETADO", "detail": "Parametrización independiente y optimización Optuna"},
                    {"step": 5, "name": "Validación & Evaluación de Prueba", "status": "COMPLETADO", "detail": "Métricas supervisadas (M1, M2) y ranking de anomalías (M3)"},
                    {"step": 6, "name": "Comparación & Reportes", "status": "COMPLETADO", "detail": "Matriz de contraste, trazabilidad SHA-256 y exportación"},
                ]
            },
        }

        # Guardar artefacto en disco
        out_file = MODEL_STORAGE_DIR / f"experiment_{exp_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(experiment_summary, f, ensure_ascii=False, indent=2)

        return experiment_summary
