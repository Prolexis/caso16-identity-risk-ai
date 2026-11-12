"""Export regression tests. AppTest downloads are UnknownElements, not widgets."""
import io
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
from reporting import build_report, dataset_hash, figure_png


@pytest.fixture
def snapshot():
    accounts = pd.DataFrame([{"id": 1, "username": "=HYPERLINK(\"bad\")", "source": "LAB", "risk_score": 75}])
    findings = pd.DataFrame([{"id": 4, "account_id": 1, "rule_id": "R02", "username": "test", "risk_score": 75, "rationale": "Privilegio <sin validar>"}])
    return accounts, findings


def test_hash_is_order_independent(snapshot):
    accounts, _ = snapshot
    assert dataset_hash(accounts) == dataset_hash(accounts[accounts.columns[::-1]])
    changed = accounts.copy()
    changed.loc[0, "risk_score"] = 0
    assert dataset_hash(changed) != dataset_hash(accounts)


def test_xlsx_content_and_formula_safety(snapshot):
    from openpyxl import load_workbook
    accounts, findings = snapshot
    wb = load_workbook(io.BytesIO(build_report("xlsx", accounts, findings, "auditor")))
    assert {"Resumen", "Cuentas", "Hallazgos", "Evaluación", "Explicabilidad", "Trazabilidad"} <= set(wb.sheetnames)
    assert wb["Resumen"]["B2"].value == 1
    assert wb["Cuentas"]["B2"].data_type == "s"
    assert wb["Cuentas"]["B2"].value.startswith("'=")
    assert wb["Cuentas"].auto_filter.ref
    assert dataset_hash(accounts) in str(list(wb["Trazabilidad"].values))


def test_docx_and_pdf_are_real_documents(snapshot):
    from docx import Document
    accounts, findings = snapshot
    doc = Document(io.BytesIO(build_report("docx", accounts, findings, "auditor")))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert dataset_hash(accounts) in text
    assert "Sin evaluación ML incluida" in text
    assert len(doc.inline_shapes) == 2
    assert float(doc.tables[0].rows[1].cells[1].text) == 1
    pdf = build_report("pdf", accounts, findings, "auditor")
    assert pdf.startswith(b"%PDF-") and b"%%EOF" in pdf


def test_figures_are_600_dpi(snapshot):
    from PIL import Image
    for kind in ("histogram", "pareto"):
        data, interpretation = figure_png(*snapshot, kind)
        image = Image.open(io.BytesIO(data))
        assert all(abs(dpi - 600) < 1 for dpi in image.info["dpi"])
        assert image.width == 4200
        assert interpretation


def test_report_view_download_contract_isolated_database(tmp_path):
    # Fresh interpreter prevents importing a previously configured production engine.
    code = '''
from streamlit.testing.v1 import AppTest
at = AppTest.from_file("app.py", default_timeout=60)
at.session_state["authenticated"] = True
at.session_state["actor"] = "auditor@demo.local"
at.session_state["role"] = "Auditor"
at.run()
assert not at.exception, str(at.exception)
at.radio[0].set_value("Reportes").run()
for fmt in ("xlsx", "docx", "pdf"):
    at.button(key=f"generate_{fmt}").click().run()
    assert not at.exception, str(at.exception)
    assert not at.error, str(at.error)
downloads = at.get("download_button")
assert len(downloads) == 3
assert {d.proto.label for d in downloads} == {"Descargar Excel (.xlsx)", "Descargar Word (.docx)", "Descargar PDF (.pdf)"}
assert all(d.proto.url for d in downloads)
assert at.session_state["report_pdf"].startswith(b"%PDF-")
'''
    env = dict(os.environ, DATABASE_URL=f"sqlite:///{(tmp_path / 'reports.db').as_posix()}", ENV="test")
    result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).parent, env=env, capture_output=True, text=True, timeout=150)
    assert result.returncode == 0, result.stdout + result.stderr
