"""Pruebas unitarias para el motor de entrenamiento M1, M2, M3 y reportes."""
import pytest
from training_engine import (
    ExperimentConfig,
    TrainingPipelineEngine,
    generate_demo_dataset,
    perform_partition_70_15_15,
)
from training_reports import (
    export_experiment_excel,
    export_experiment_pdf,
    export_experiment_word,
)


def test_partition_70_15_15_no_leakage():
    data = generate_demo_dataset(n=100, seed=123)
    labels = ["Crítico" if i % 3 == 0 else "Alto" if i % 2 == 0 else "Medio" for i in range(100)]
    splits = perform_partition_70_15_15(data, labels, seed=42, stratify=True)

    tr = set(splits["train"])
    va = set(splits["val"])
    te = set(splits["test"])

    # Disjuntos (no leakage)
    assert not (tr & va)
    assert not (tr & te)
    assert not (va & te)

    # Total 100
    assert len(tr | va | te) == 100
    assert 65 <= len(tr) <= 75
    assert 12 <= len(va) <= 18
    assert 12 <= len(te) <= 18


def test_full_pipeline_m1_m2_m3():
    data = generate_demo_dataset(n=60, seed=42)
    engine = TrainingPipelineEngine()

    cfg = ExperimentConfig(
        run_m1=True,
        run_m2=True,
        run_m3=True,
        use_optuna=True,
        optuna_trials_m1=2,
        optuna_trials_m2=2,
        timeout_seconds=30.0,
        seed=42,
    )

    result = engine.run_full_experiment(data, cfg)

    assert result["status"] == "completed"
    assert "experiment_id" in result
    assert "dataset_hash" in result
    assert "M1_RandomForest" in result["models"]
    assert "M2_XGBoost" in result["models"]
    assert "M3_IsolationForest" in result["models"]

    # Verificar métricas de M1
    m1_res = result["models"]["M1_RandomForest"]
    assert "accuracy" in m1_res["test_metrics"]
    assert "f1_macro" in m1_res["test_metrics"]
    assert "confusion_matrix" in m1_res["test_metrics"]

    # Verificar M3 (No Supervisado)
    m3_res = result["models"]["M3_IsolationForest"]
    assert m3_res["model_type"].startswith("No Supervisado")
    assert "top_anomalies" in m3_res
    assert len(m3_res["top_anomalies"]) > 0

    # Verificar tabla comparativa
    assert len(result["comparison_table"]) > 0

    # Verificar exportación de reportes
    pdf_bytes = export_experiment_pdf(result)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")

    docx_bytes = export_experiment_word(result)
    assert len(docx_bytes) > 500

    xlsx_bytes = export_experiment_excel(result)
    assert len(xlsx_bytes) > 500
