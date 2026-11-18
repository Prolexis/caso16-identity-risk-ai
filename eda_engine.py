"""Módulo de Análisis Exploratorio de Datos (EDA) y Diagnóstico de Calidad.

Específico para telemetría de identidades Active Directory / LDAP en CASO16.
Analiza nulos, duplicados, outliers, desbalance de clases, atributos temporales de AD
(lastLogon vs lastLogonTimestamp) y genera diagnósticos reproducibles.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
from typing import Any
import numpy as np
import pandas as pd


def _calculate_days(val: Any, ref_date: date) -> float | None:
    if val is None or str(val).strip() in ("NaT", "nan", "None", ""):
        return None
    try:
        dt = date.fromisoformat(str(val)[:10])
        return max(0, (ref_date - dt).days)
    except Exception:
        return None


def run_eda(accounts_data: list[dict[str, Any]] | pd.DataFrame, reference_date: date | None = None) -> dict[str, Any]:
    """Ejecuta un análisis exploratorio exhaustivo sobre el inventario de cuentas."""
    ref_date = reference_date or date.today()
    if isinstance(accounts_data, list):
        df = pd.DataFrame(accounts_data)
    else:
        df = accounts_data.copy()

    total_records = len(df)
    if total_records == 0:
        return {
            "total_records": 0,
            "status": "empty",
            "message": "No hay registros disponibles para el análisis exploratorio.",
        }

    # 1. Resumen estructural y tipos
    columns_info = []
    for col in df.columns:
        n_missing = int(df[col].isna().sum())
        dtype_str = str(df[col].dtype)
        columns_info.append({
            "name": col,
            "dtype": dtype_str,
            "missing_count": n_missing,
            "missing_pct": round((n_missing / total_records) * 100, 2),
            "unique_values": int(df[col].nunique(dropna=False)),
        })

    # 2. Detección de Duplicados e Integridad
    dup_ids = int(df["external_id"].duplicated().sum()) if "external_id" in df.columns else 0
    dup_usernames = int(df["username"].duplicated().sum()) if "username" in df.columns else 0
    full_duplicates = int(df.duplicated().sum())

    # 3. Análisis de Atributos Críticos de Active Directory (lastLogon / lastLogonTimestamp)
    last_act_col = "last_activity" if "last_activity" in df.columns else None
    days_series = df[last_act_col].apply(lambda x: _calculate_days(x, ref_date)) if last_act_col else pd.Series([], dtype=float)
    valid_activities = days_series.dropna()

    no_logon_count = int(total_records - len(valid_activities))
    no_logon_pct = round((no_logon_count / total_records) * 100, 2)
    inactive_90d_count = int((valid_activities >= 90).sum())
    inactive_90d_pct = round((inactive_90d_count / total_records) * 100, 2)

    ad_telemetry_diagnostic = {
        "attribute_evaluated": "last_activity (mapeado desde lastLogon / lastLogonTimestamp de AD)",
        "accounts_without_logon": no_logon_count,
        "accounts_without_logon_pct": no_logon_pct,
        "accounts_inactive_90_days_or_more": inactive_90d_count,
        "accounts_inactive_90_days_or_more_pct": inactive_90d_pct,
        "ad_technical_warning": (
            "En Active Directory, 'lastLogon' no se replica entre Domain Controllers (DC); reside únicamente "
            "en el DC que autenticó la sesión. 'lastLogonTimestamp' sí se replica, pero con un intervalo de retardo "
            "de hasta 9 a 14 días para evitar tormentas de replicación. Por lo tanto, una fecha no registrada no debe "
            "asumirse inmediatamente como abandono definitivo sin verificar todos los DCs o correlacionar con eventos de Kerberos."
        ),
    }

    # 4. Distribución de Variables Categóricas
    account_types = df["account_type"].value_counts().to_dict() if "account_type" in df.columns else {}
    sources = df["source"].value_counts().to_dict() if "source" in df.columns else {}

    boolean_flags = {}
    for flag in ["active", "is_admin", "justification_verified", "is_duplicate", "password_never_expires"]:
        if flag in df.columns:
            true_count = int((df[flag] == True).sum())  # noqa: E712
            boolean_flags[flag] = {
                "true_count": true_count,
                "false_count": total_records - true_count,
                "true_pct": round((true_count / total_records) * 100, 2),
            }

    # 5. Outliers y Dispersión Numérica
    numeric_stats = {}
    if "risk_score" in df.columns:
        scores = pd.to_numeric(df["risk_score"], errors="coerce").dropna()
        if len(scores) > 0:
            q1 = float(scores.quantile(0.25))
            q3 = float(scores.quantile(0.75))
            iqr = q3 - q1
            outliers = scores[(scores < (q1 - 1.5 * iqr)) | (scores > (q3 + 1.5 * iqr))]
            numeric_stats["risk_score"] = {
                "mean": round(float(scores.mean()), 2),
                "std": round(float(scores.std(ddof=1)), 2) if len(scores) > 1 else 0.0,
                "median": float(scores.median()),
                "min": float(scores.min()),
                "max": float(scores.max()),
                "q1": q1,
                "q3": q3,
                "iqr": round(iqr, 2),
                "outliers_count": len(outliers),
            }

    if len(valid_activities) > 0:
        q1 = float(valid_activities.quantile(0.25))
        q3 = float(valid_activities.quantile(0.75))
        iqr = q3 - q1
        outliers = valid_activities[(valid_activities < (q1 - 1.5 * iqr)) | (valid_activities > (q3 + 1.5 * iqr))]
        numeric_stats["inactivity_days"] = {
            "mean": round(float(valid_activities.mean()), 2),
            "std": round(float(valid_activities.std(ddof=1)), 2) if len(valid_activities) > 1 else 0.0,
            "median": float(valid_activities.median()),
            "min": float(valid_activities.min()),
            "max": float(valid_activities.max()),
            "q1": q1,
            "q3": q3,
            "iqr": round(iqr, 2),
            "outliers_count": len(outliers),
        }

    # 6. Distribución de Severidad y Desbalance de Clases
    # Si existe risk_score, mapear a clases de severidad deterministas
    if "risk_score" in df.columns:
        def _to_severity(s):
            val = float(s) if pd.notna(s) else 0.0
            if val >= 80:
                return "Crítico"
            if val >= 60:
                return "Alto"
            if val >= 35:
                return "Medio"
            return "Bajo"
        severities = df["risk_score"].apply(_to_severity)
    else:
        severities = pd.Series(["No etiquetado"] * total_records)

    class_counts = severities.value_counts().to_dict()
    class_distribution = {
        cls: {
            "count": int(cnt),
            "percentage": round((cnt / total_records) * 100, 2),
        }
        for cls, cnt in class_counts.items()
    }

    min_class_count = min(class_counts.values()) if class_counts else 0
    max_class_count = max(class_counts.values()) if class_counts else 0
    imbalance_ratio = round(max_class_count / min_class_count, 2) if min_class_count > 0 else 0.0

    # 7. Diagnóstico General y Recomendaciones de Preprocesamiento
    recommendations = []
    if no_logon_count > 0:
        recommendations.append(
            f"Hay {no_logon_count} cuentas ({no_logon_pct}%) sin registro de last_activity. "
            "Se requiere imputación basada en la mediana o valor nulo explícito y un indicador binario de ausencia "
            "ajustado exclusivamente en el conjunto de entrenamiento para evitar fuga de información."
        )
    if dup_ids > 0 or dup_usernames > 0:
        recommendations.append(
            f"Se detectaron {dup_ids} IDs duplicados y {dup_usernames} usernames repetidos. "
            "Deduplicar antes de particionar para prevenir que la misma identidad aparezca simultáneamente en train y test."
        )
    if imbalance_ratio > 3.0:
        recommendations.append(
            f"Desbalance de clases detectado (ratio {imbalance_ratio}:1). "
            "Para los modelos M1 (Random Forest) y M2 (XGBoost), utilizar pesos balanceados (class_weight='balanced') "
            "y estratificación en la partición 70/15/15."
        )
    recommendations.append(
        "Preservar rigurosamente el 15% de prueba (Test) como conjunto ciego. "
        "No utilizar los datos de test en ningún paso del tuning de hiperparámetros con Optuna."
    )

    canonical_bytes = json.dumps(
        sorted([dict(r) for r in df.to_dict(orient="records")], key=lambda x: str(x.get("id", ""))),
        default=str,
        sort_keys=True,
    ).encode()
    dataset_hash = hashlib.sha256(canonical_bytes).hexdigest()

    return {
        "total_records": total_records,
        "dataset_hash": dataset_hash,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "columns_summary": columns_info,
        "integrity": {
            "duplicate_external_ids": dup_ids,
            "duplicate_usernames": dup_usernames,
            "full_row_duplicates": full_duplicates,
        },
        "active_directory_telemetry": ad_telemetry_diagnostic,
        "categorical_distributions": {
            "account_types": account_types,
            "sources_domains": sources,
            "security_flags": boolean_flags,
        },
        "numeric_dispersion": numeric_stats,
        "target_class_distribution": {
            "classes": class_distribution,
            "imbalance_ratio": imbalance_ratio,
            "minority_class_count": min_class_count,
        },
        "recommendations": recommendations,
    }
