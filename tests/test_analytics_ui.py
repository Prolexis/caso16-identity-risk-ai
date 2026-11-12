import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from reporting import descriptive_tables
from optuna_ui import validate_search_space


def test_search_space_validation():
    assert validate_search_space('{}') == {}
    assert validate_search_space('{"learning_rate":{"low":0.01,"high":0.3,"log":true}}')
    for invalid in ('[]', '{"depth":{"low":8,"high":2}}', '{"x":{"choices":[]}}', '{"lr":{"low":0,"high":1,"log":true}}'):
        with pytest.raises(ValueError):
            validate_search_space(invalid)


def test_descriptive_summary_uses_actual_population():
    accounts = pd.DataFrame({"source": ["A", "A", "B"], "risk_score": [0, 100, 60]})
    findings = pd.DataFrame({"rule_id": ["R01", "R01", "R02"], "risk_score": [0, 100, 60]})
    domains, rules = descriptive_tables(accounts, findings)
    assert domains.n.sum() == 3
    assert domains.loc[domains.source == "A", "media"].iloc[0] == 50
    assert rules.iloc[-1].acumulado_pct == pytest.approx(100)
    assert domains["Interpretación"].str.contains("cuentas").all()


def test_evaluation_unavailable_does_not_invent_metrics():
    def script():
        import analytics_ui
        def unavailable(*args, **kwargs):
            raise RuntimeError("API no disponible")
        from unittest.mock import patch
        with patch.object(analytics_ui, "api_request", unavailable):
            analytics_ui.render_evaluation()
    at = AppTest.from_function(script).run()
    assert not at.exception
    assert "API no disponible" in at.info[0].value
    assert not at.metric


def test_training_payload_and_job_monitor(monkeypatch):
    import optuna_ui
    calls = []
    def fake(method, path, payload=None):
        calls.append((method, path, payload))
        if method == "POST":
            return {"id": "test-job", "status": "queued"}
        return {"id": "test-job", "status": "running", "progress": {"fold": 1, "trial": 2}}
    monkeypatch.setattr(optuna_ui, "api_request", fake)
    at = AppTest.from_string("from optuna_ui import render_training\nrender_training()").run()
    assert not at.exception
    next(b for b in at.button if b.label == "Iniciar CV anidada").click().run()
    assert not at.exception
    sent = next(payload for method, path, payload in calls if method == "POST")
    assert sent["outer_folds"] == 5 and sent["inner_folds"] == 3
    assert sent["stratify"] == "joint" and sent["seed"] == 42
    assert at.session_state["training_job_id"] == "test-job"
