"""Pruebas unitarias para el motor de Análisis Exploratorio de Datos (EDA)."""
from datetime import date
import pytest
from eda_engine import run_eda
from training_engine import generate_demo_dataset


def test_eda_engine_with_demo_dataset():
    data = generate_demo_dataset(n=50, seed=42)
    result = run_eda(data)

    assert result["total_records"] == 50
    assert "dataset_hash" in result
    assert len(result["dataset_hash"]) == 64
    assert "columns_summary" in result
    assert "active_directory_telemetry" in result

    # Verificar diagnóstico AD
    ad = result["active_directory_telemetry"]
    assert "ad_technical_warning" in ad
    assert "accounts_without_logon" in ad
    assert "accounts_inactive_90_days_or_more" in ad

    # Verificar clases objetivo
    classes = result["target_class_distribution"]["classes"]
    assert len(classes) >= 1
    assert len(result["recommendations"]) >= 1


def test_eda_engine_empty_dataset():
    result = run_eda([])
    assert result["total_records"] == 0
    assert result["status"] == "empty"
