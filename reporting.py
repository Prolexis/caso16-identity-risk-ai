"""Pure, reproducible audit exports; no database access or invented ML results."""
from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime, timezone
from xml.sax.saxutils import escape

import pandas as pd

MODEL_VERSION = "deterministic-R01-R06"


def dataset_hash(accounts: pd.DataFrame) -> str:
    """Hash canonical records, independent of input row/column order."""
    records = accounts.reindex(sorted(accounts.columns), axis=1).to_json(orient="records", date_format="iso", default_handler=str)
    canonical = sorted(json.loads(records), key=lambda row: json.dumps(row, sort_keys=True))
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def traceability(accounts, actor, generated_at=None):
    return {"dataset_sha256": dataset_hash(accounts), "model_version": MODEL_VERSION,
            "actor": actor, "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
            "methodology": "R01–R06; score determinista primario. ML no evaluado en este reporte."}


def summary_table(accounts, findings):
    scores = pd.to_numeric(accounts.get("risk_score", pd.Series(dtype=float)), errors="coerce")
    high = int(scores.ge(60).sum())
    return pd.DataFrame([
        {"Métrica": "Cuentas", "Valor": len(accounts), "Interpretación": "Identidades presentes en la instantánea exportada."},
        {"Métrica": "Score >= 60", "Valor": high, "Interpretación": f"{high / len(accounts):.1%} requieren priorización." if len(accounts) else "Sin cuentas para evaluar."},
        {"Métrica": "Hallazgos", "Valor": len(findings), "Interpretación": "Una cuenta puede presentar varias reglas; no equivale a cuentas únicas."},
        {"Métrica": "Riesgo acumulado", "Valor": float(scores.sum()), "Interpretación": "Suma de scores; no es una probabilidad de ataque."},
    ])


def descriptive_tables(accounts, findings):
    if accounts.empty:
        return pd.DataFrame(), pd.DataFrame()
    domain = accounts.groupby("source", dropna=False).risk_score.agg(n="count", media="mean", mediana="median", desviacion="std", minimo="min", maximo="max").reset_index()
    domain["porcentaje"] = domain.n / len(accounts) * 100
    domain["Interpretación"] = domain.apply(lambda r: f"{r['source']}: {int(r['n'])} cuentas ({r['porcentaje']:.1f}%), score medio {r['media']:.1f}; dispersión descriptiva, no incertidumbre ML.", axis=1)
    if findings.empty:
        return domain, pd.DataFrame()
    rules = findings.groupby("rule_id").risk_score.agg(n="count", media="mean", mediana="median", desviacion="std", minimo="min", maximo="max").reset_index().sort_values("n", ascending=False)
    rules["porcentaje"] = rules.n / len(findings) * 100
    rules["acumulado_pct"] = rules.porcentaje.cumsum()
    rules["Interpretación"] = rules.apply(lambda r: f"{r['rule_id']}: {int(r['n'])} hallazgos, {r['porcentaje']:.1f}% del total; comprobar evidencia antes de remediar.", axis=1)
    return domain, rules


def figure_png(accounts, findings, kind="histogram") -> tuple[bytes, str]:
    """Render actual descriptive data at 600 DPI, never substitute fake ML plots."""
    from matplotlib.figure import Figure
    fig = Figure(figsize=(7, 4), layout="constrained")
    ax = fig.subplots()
    if kind == "histogram":
        scores = pd.to_numeric(accounts.get("risk_score", pd.Series(dtype=float)), errors="coerce").dropna()
        ax.hist(scores, bins=list(range(0, 101, 10)), color="#168aad", edgecolor="white", label="Cuentas")
        ax.axvline(60, color="#e97721", linestyle="--", label="Prioridad descriptiva >=60")
        ax.set(title="Distribución de score determinista", xlabel="Score (0–100)", ylabel="Cuentas")
        text = f"{int(scores.ge(60).sum())} de {len(scores)} cuentas tienen score >=60. Este histograma no mide precisión predictiva."
    elif kind == "pareto":
        counts = findings.get("rule_id", pd.Series(dtype=str)).value_counts()
        ax.bar(counts.index, counts.values, color="#168aad", label="Hallazgos")
        ax.set(title="Pareto de hallazgos por regla", xlabel="Regla", ylabel="Hallazgos")
        if len(counts):
            right = ax.twinx()
            right.plot(counts.index, counts.cumsum() / counts.sum() * 100, color="#e97721", marker="o", label="Acumulado %")
            right.set(ylabel="Porcentaje acumulado", ylim=(0, 105))
            right.legend(loc="upper right")
        text = f"{counts.index[0]} concentra {counts.iloc[0]} de {counts.sum()} hallazgos; priorizar validación de su evidencia." if len(counts) else "No hay hallazgos para ordenar."
    else:
        raise ValueError("Unsupported descriptive figure")
    ax.legend(loc="upper left")
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=600)
    return buffer.getvalue(), text


def build_report(format, accounts, findings, actor, evaluation=None, generated_at=None) -> bytes:
    """Build bytes from a snapshot. Caller owns authorization and audit recording."""
    if format not in {"xlsx", "docx", "pdf"}:
        raise ValueError("Formato no soportado")
    trace = traceability(accounts, actor, generated_at)
    summary = summary_table(accounts, findings)
    acc = accounts.copy()
    acc["Interpretación"] = acc.get("risk_score", pd.Series(index=acc.index, dtype=float)).map(lambda s: f"Score determinista {s}; validar reglas y evidencia.")
    found = findings.copy()
    found["Interpretación"] = found.get("rationale", pd.Series("Revisar evidencia de la regla.", index=found.index))
    evaluation_table = pd.DataFrame([{"Estado": "Sin evaluación ML incluida", "Interpretación": "No se presentan matrices, ROC/PR ni SHAP inexistentes."}]) if evaluation is None else pd.DataFrame([{"Resultado registrado": json.dumps(evaluation, ensure_ascii=False, default=str), "Interpretación": "Evaluación proporcionada; consultar partición y métricas registradas."}])
    if format == "xlsx":
        from openpyxl.styles import Font
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            tables = {"Resumen": summary, "Cuentas": acc, "Hallazgos": found, "Evaluación": evaluation_table,
                      "Explicabilidad": pd.DataFrame([{"Método": MODEL_VERSION, "Interpretación": "Reglas auditables; Grad-CAM no aplica a datos tabulares."}]),
                      "Trazabilidad": pd.DataFrame(list(trace.items()), columns=["Campo", "Valor"])}
            for name, frame in tables.items():
                safe = frame.copy()
                for col in safe:
                    safe[col] = safe[col].map(lambda v: "'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else str(v) if isinstance(v, (dict, list)) else v)
                    if isinstance(safe[col].dtype, pd.DatetimeTZDtype):
                        safe[col] = safe[col].astype(str)
                safe.to_excel(writer, sheet_name=name, index=False)
                ws = writer.sheets[name]
                ws.freeze_panes = "A2"
                ws.auto_filter.ref = ws.dimensions
                for cell in ws[1]:
                    cell.font = Font(bold=True)
        return out.getvalue()
    figures = [figure_png(accounts, findings, kind) for kind in ("histogram", "pareto")]
    if format == "docx":
        from docx import Document
        from docx.shared import Inches
        doc = Document()
        doc.add_heading("CASO16 · Auditoría de identidades", 0)
        doc.add_heading("Trazabilidad y metodología", 1)
        for key, value in trace.items():
            doc.add_paragraph(f"{key}: {value}")
        doc.add_heading("Resumen ejecutivo", 1)
        table = doc.add_table(rows=1, cols=3)
        table.style = "Light Shading Accent 1"
        for cell, col in zip(table.rows[0].cells, summary.columns):
            cell.text = col
        for row in summary.itertuples(index=False, name=None):
            for cell, value in zip(table.add_row().cells, row):
                cell.text = str(value)
        doc.add_heading("Resultados descriptivos", 1)
        for image, text in figures:
            doc.add_picture(io.BytesIO(image), width=Inches(6))
            doc.add_paragraph(text)
        doc.add_heading("Evaluación y limitaciones", 1)
        doc.add_paragraph(evaluation_table.to_string(index=False))
        doc.add_heading("Anexo · Hallazgos", 1)
        for row in found.to_dict("records"):
            doc.add_paragraph(f"#{row.get('id')} · {row.get('rule_id')} · {row.get('username')}: {row.get('Interpretación')}")
        out = io.BytesIO()
        doc.save(out)
        return out.getvalue()
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table
    from reportlab.lib.pagesizes import A4
    styles = getSampleStyleSheet()
    out = io.BytesIO()
    elements = [Paragraph("CASO16 · Auditoría de identidades", styles["Title"])]
    for key, value in trace.items():
        elements.append(Paragraph(escape(f"{key}: {value}"), styles["Normal"]))
    elements.append(Paragraph("Resumen ejecutivo", styles["Heading1"]))
    rows = [[Paragraph(escape(str(v)), styles["Normal"]) for v in row] for row in [summary.columns.tolist()] + summary.values.tolist()]
    elements.extend([Table(rows, colWidths=[110, 55, 330], repeatRows=1), Spacer(1, 12)])
    for image, text in figures:
        elements.extend([Image(io.BytesIO(image), width=490, height=280), Paragraph(escape(text), styles["Normal"])])
    elements.append(Paragraph("Evaluación y limitaciones", styles["Heading1"]))
    elements.append(Paragraph(escape(evaluation_table.to_string(index=False)), styles["Normal"]))
    elements.append(Paragraph("Anexo · Hallazgos", styles["Heading1"]))
    for row in found.to_dict("records"):
        elements.append(Paragraph(escape(f"#{row.get('id')} · {row.get('rule_id')} · {row.get('username')}: {row.get('Interpretación')}"), styles["Normal"]))
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.drawString(40, 20, f"CASO16 | {trace['generated_at']} | Página {doc.page}")
        canvas.restoreState()
    SimpleDocTemplate(out, pagesize=A4, leftMargin=40, rightMargin=40).build(elements, onFirstPage=footer, onLaterPages=footer)
    return out.getvalue()
