"""Generación de Reportes Ejecutivos y Académicos en PDF, Word (.docx) y Excel (.xlsx).

Exporta los resultados detallados del Motor de Entrenamiento de Inteligencia Artificial (CASO16).
Garantiza trazabilidad criptográfica (SHA-256), rigor metodológico y auditoría formal.
"""
from __future__ import annotations

import base64
import io
import json
from typing import Any
import pandas as pd

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def export_experiment_excel(experiment_data: dict[str, Any], actor: str = "auditor@demo.local") -> bytes:
    """Genera un archivo Excel (.xlsx) exhaustivo con hojas de Resumen, Métricas, M1, M2, M3 y Trazabilidad."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # 1. Resumen Ejecutivo
        summary_rows = [
            {"Campo": "ID de Experimento", "Valor": experiment_data.get("experiment_id", "")},
            {"Campo": "Estado", "Valor": experiment_data.get("status", "")},
            {"Campo": "Inicio", "Valor": experiment_data.get("started_at", "")},
            {"Campo": "Finalización", "Valor": experiment_data.get("completed_at", "")},
            {"Campo": "Duración (segundos)", "Valor": experiment_data.get("elapsed_seconds", 0)},
            {"Campo": "Hash Dataset (SHA-256)", "Valor": experiment_data.get("dataset_hash", "")},
            {"Campo": "Total Registros", "Valor": experiment_data.get("total_records", 0)},
            {"Campo": "Actor / Auditor", "Valor": actor},
            {"Campo": "Partición Entrenamiento (70%)", "Valor": experiment_data.get("partition", {}).get("train_count", 0)},
            {"Campo": "Partición Validación (15%)", "Valor": experiment_data.get("partition", {}).get("val_count", 0)},
            {"Campo": "Partición Prueba Ciega (15%)", "Valor": experiment_data.get("partition", {}).get("test_count", 0)},
        ]
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name="Resumen", index=False)

        # 2. Comparativa Supervisada (M1 vs M2)
        comp_table = experiment_data.get("comparison_table", [])
        if comp_table:
            pd.DataFrame(comp_table).to_excel(writer, sheet_name="Comparativa_M1_vs_M2", index=False)

        # 3. Métricas Detalladas M1 (Random Forest)
        m1 = experiment_data.get("models", {}).get("M1_RandomForest", {})
        if m1:
            m1_metrics = []
            for split_name in ["validation_metrics", "test_metrics"]:
                met = m1.get(split_name, {})
                for k in ["accuracy", "precision_macro", "recall_macro", "f1_macro", "f1_weighted", "roc_auc", "pr_auc", "mcc"]:
                    m1_metrics.append({"Partición": split_name.replace("_metrics", "").upper(), "Métrica": k, "Valor": met.get(k)})
            pd.DataFrame(m1_metrics).to_excel(writer, sheet_name="M1_RandomForest", index=False)

        # 4. Métricas Detalladas M2 (XGBoost)
        m2 = experiment_data.get("models", {}).get("M2_XGBoost", {})
        if m2:
            m2_metrics = []
            for split_name in ["validation_metrics", "test_metrics"]:
                met = m2.get(split_name, {})
                for k in ["accuracy", "precision_macro", "recall_macro", "f1_macro", "f1_weighted", "roc_auc", "pr_auc", "mcc"]:
                    m2_metrics.append({"Partición": split_name.replace("_metrics", "").upper(), "Métrica": k, "Valor": met.get(k)})
            pd.DataFrame(m2_metrics).to_excel(writer, sheet_name="M2_XGBoost", index=False)

        # 5. Detección de Anomalías M3 (Isolation Forest)
        m3 = experiment_data.get("models", {}).get("M3_IsolationForest", {})
        if m3:
            top_anom = m3.get("top_anomalies", [])
            if top_anom:
                pd.DataFrame(top_anom).to_excel(writer, sheet_name="M3_Top_Anomalias", index=False)

        # 6. Metodología y Trazabilidad
        phases = experiment_data.get("methodology_diagram", {}).get("phases", [])
        if phases:
            pd.DataFrame(phases).to_excel(writer, sheet_name="Metodologia", index=False)

    return output.getvalue()


def export_experiment_word(experiment_data: dict[str, Any], actor: str = "auditor@demo.local") -> bytes:
    """Genera un informe técnico formal en formato Word (.docx)."""
    doc = Document()

    # Título Principal
    title = doc.add_heading("CASO16 — Reporte Técnico de Entrenamiento de Modelos IA", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    sub = doc.add_paragraph("Gobierno de Identidades, Detección de Cuentas Huérfanas y Privilegios Excesivos")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"Generado por: {actor} | Fecha: {experiment_data.get('completed_at', '')}")
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # 1. Resumen Ejecutivo y Trazabilidad
    doc.add_heading("1. Ficha Técnica y Trazabilidad", level=1)
    p_meta = doc.add_paragraph()
    p_meta.add_run(f"• ID del Experimento: ").bold = True
    p_meta.add_run(f"{experiment_data.get('experiment_id', '')}\n")
    p_meta.add_run(f"• Hash Criptográfico Dataset (SHA-256): ").bold = True
    p_meta.add_run(f"{experiment_data.get('dataset_hash', '')}\n")
    p_meta.add_run(f"• Tiempo de Ejecución: ").bold = True
    p_meta.add_run(f"{experiment_data.get('elapsed_seconds', 0)} segundos\n")
    p_meta.add_run(f"• Partición de Datos: ").bold = True
    part = experiment_data.get("partition", {})
    p_meta.add_run(f"70% Entrenamiento ({part.get('train_count', 0)}), 15% Validación ({part.get('val_count', 0)}), 15% Prueba ({part.get('test_count', 0)})\n")

    # 2. Metodología de 6 Fases
    doc.add_heading("2. Metodología Experimental Implementada", level=1)
    phases = experiment_data.get("methodology_diagram", {}).get("phases", [])
    table_m = doc.add_table(rows=1, cols=3)
    table_m.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table_m.rows[0].cells
    hdr[0].text = "Fase"
    hdr[1].text = "Nombre"
    hdr[2].text = "Alcance y Control Antifuga"
    for ph in phases:
        row = table_m.add_row().cells
        row[0].text = str(ph.get("step", ""))
        row[1].text = str(ph.get("name", ""))
        row[2].text = str(ph.get("detail", ""))

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # 3. Modelos Supervisados: M1 (Random Forest) y M2 (XGBoost)
    doc.add_heading("3. Evaluación de Modelos Supervisados (M1 vs M2)", level=1)
    doc.add_paragraph(
        "M1 (Random Forest) y M2 (XGBoost) fueron entrenados para predecir la severidad y necesidad de remediación. "
        "La optimización de hiperparámetros se realizó exclusivamente con Optuna TPE sobre los conjuntos de "
        "entrenamiento y validación interna. El conjunto de Prueba (15%) se mantuvo completamente ciego."
    )

    comp_table = experiment_data.get("comparison_table", [])
    if comp_table:
        table_c = doc.add_table(rows=1, cols=4)
        table_c.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_c = table_c.rows[0].cells
        hdr_c[0].text = "Métrica (Test Ciego)"
        hdr_c[1].text = "M1 (Random Forest)"
        hdr_c[2].text = "M2 (XGBoost)"
        hdr_c[3].text = "Modelo Superior"
        for row in comp_table:
            c_cells = table_c.add_row().cells
            c_cells[0].text = str(row.get("metric", ""))
            c_cells[1].text = str(row.get("m1_random_forest", "-"))
            c_cells[2].text = str(row.get("m2_xgboost", "-"))
            c_cells[3].text = str(row.get("best_model", "-"))

    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # 4. Detección de Anomalías no Supervisada: M3 (Isolation Forest)
    doc.add_heading("4. Detección de Anomalías no Supervisada (M3: Isolation Forest)", level=1)
    m3 = experiment_data.get("models", {}).get("M3_IsolationForest", {})
    if m3:
        p_m3 = doc.add_paragraph()
        p_m3.add_run(f"• Total Evaluado: {m3.get('total_evaluated', 0)} cuentas\n")
        p_m3.add_run(f"• Cuentas Anómalas Detectadas: {m3.get('anomalies_detected', 0)} ({m3.get('anomaly_rate_pct', 0)}%)\n")
        p_m3.add_run(f"• Condición de Parada: {m3.get('stopping_condition', '')}\n")

        doc.add_paragraph(f"Nota Metodológica: {m3.get('methodological_note', '')}")

        top_anom = m3.get("top_anomalies", [])[:5]
        if top_anom:
            doc.add_heading("Top Cuentas con Mayor Desviación Anómala:", level=2)
            table_a = doc.add_table(rows=1, cols=5)
            table_a.alignment = WD_TABLE_ALIGNMENT.CENTER
            h_a = table_a.rows[0].cells
            h_a[0].text = "Rank"
            h_a[1].text = "Username"
            h_a[2].text = "Dominio AD"
            h_a[3].text = "Score Anomalía"
            h_a[4].text = "Admin"
            for a in top_anom:
                r_a = table_a.add_row().cells
                r_a[0].text = str(a.get("rank", ""))
                r_a[1].text = str(a.get("username", ""))
                r_a[2].text = str(a.get("source", ""))
                r_a[3].text = str(a.get("anomaly_score", ""))
                r_a[4].text = "Sí" if a.get("is_admin") else "No"

    # 5. Imágenes incrustadas si existen
    charts = experiment_data.get("charts", {})
    if charts:
        doc.add_heading("5. Evidencias Gráficas del Proceso de Entrenamiento", level=1)
        for chart_name, b64_str in charts.items():
            if b64_str:
                try:
                    img_data = base64.b64decode(b64_str)
                    img_io = io.BytesIO(img_data)
                    doc.add_heading(f"Gráfico: {chart_name.replace('_', ' ').title()}", level=2)
                    doc.add_picture(img_io, width=Inches(5.5))
                except Exception:
                    pass

    # 6. Conclusiones y Advertencia Académica
    doc.add_heading("6. Conclusiones y Advertencias Técnicas", level=1)
    doc.add_paragraph(
        "1. Las reglas deterministas R01–R06 constituyen la fuente de autoridad normativa verificable en CASO16. "
        "Los modelos de Machine Learning (M1 y M2) actúan como aceleradores de priorización y segundas opiniones analíticas, "
        "nunca como reemplazo de la auditoría de cumplimiento.\n"
        "2. El modelo M3 opera de manera no supervisada y permite descubrir identidades con configuraciones atípicas "
        "que escapan a las reglas estáticas predefinidas.\n"
        "3. Cualquier despliegue a producción requiere aprobación humana explícita (Human-in-the-loop) conforme al estándar ISO 27001."
    )

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


def export_experiment_pdf(experiment_data: dict[str, Any], actor: str = "auditor@demo.local") -> bytes:
    """Genera un reporte PDF con ReportLab incluyendo tablas estructuradas y trazabilidad."""
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )
    h1_style = ParagraphStyle(
        "H1Style",
        parent=styles["Heading2"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0369a1"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
    )

    story = []

    # Encabezado
    story.append(Paragraph("CASO16 — Reporte de Entrenamiento y Comparación de Modelos IA", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Auditor: {actor} | Fecha: {experiment_data.get('completed_at', '')} | ID: {experiment_data.get('experiment_id', '')}", subtitle_style))
    story.append(Spacer(1, 12))

    # Trazabilidad
    story.append(Paragraph("1. Ficha Técnica y Trazabilidad Criptográfica", h1_style))
    meta_table_data = [
        ["Parámetro", "Valor"],
        ["Hash SHA-256 Dataset", str(experiment_data.get("dataset_hash", ""))[:48] + "..."],
        ["Duración de Ejecución", f"{experiment_data.get('elapsed_seconds', 0)} segundos"],
        ["Total Cuentas Evaluadas", str(experiment_data.get("total_records", 0))],
        ["Partición 70% Train", str(experiment_data.get("partition", {}).get("train_count", 0))],
        ["Partición 15% Validation", str(experiment_data.get("partition", {}).get("val_count", 0))],
        ["Partición 15% Test (Ciega)", str(experiment_data.get("partition", {}).get("test_count", 0))],
    ]
    t_meta = Table(meta_table_data, colWidths=[180, 360])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # Comparativa M1 vs M2
    story.append(Paragraph("2. Comparativa Supervisada en Conjunto de Prueba Ciego (15%)", h1_style))
    comp_table = experiment_data.get("comparison_table", [])
    if comp_table:
        comp_data = [["Métrica", "M1 (Random Forest)", "M2 (XGBoost)", "Modelo Superior"]]
        for row in comp_table:
            comp_data.append([
                str(row.get("metric", "")),
                str(row.get("m1_random_forest", "-")),
                str(row.get("m2_xgboost", "-")),
                str(row.get("best_model", "-")),
            ])
        t_comp = Table(comp_data, colWidths=[140, 130, 130, 140])
        t_comp.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t_comp)
    story.append(Spacer(1, 10))

    # M3 Isolation Forest
    story.append(Paragraph("3. Detección no Supervisada de Anomalías (M3: Isolation Forest)", h1_style))
    m3 = experiment_data.get("models", {}).get("M3_IsolationForest", {})
    if m3:
        desc = (
            f"<b>Cuentas marcadas como anómalas:</b> {m3.get('anomalies_detected', 0)} "
            f"({m3.get('anomaly_rate_pct', 0)}% de la población total).<br/>"
            f"<b>Condición de parada:</b> {m3.get('stopping_condition', '')}.<br/>"
            f"<b>Rigor Metodológico:</b> {m3.get('methodological_note', '')}"
        )
        story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 6))

        top_anom = m3.get("top_anomalies", [])[:5]
        if top_anom:
            anom_data = [["Rank", "Username", "Dominio AD", "Score Anomalía", "Admin"]]
            for a in top_anom:
                anom_data.append([
                    str(a.get("rank", "")),
                    str(a.get("username", "")),
                    str(a.get("source", "")),
                    str(a.get("anomaly_score", "")),
                    "Sí" if a.get("is_admin") else "No",
                ])
            t_anom = Table(anom_data, colWidths=[40, 180, 180, 80, 60])
            t_anom.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b45309")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(t_anom)
    story.append(Spacer(1, 10))

    # Gráficos si están disponibles
    charts = experiment_data.get("charts", {})
    for chart_name, b64_str in charts.items():
        if b64_str:
            try:
                img_data = base64.b64decode(b64_str)
                img_io = io.BytesIO(img_data)
                story.append(KeepTogether([
                    Paragraph(f"Gráfico: {chart_name.replace('_', ' ').title()}", h1_style),
                    RLImage(img_io, width=420, height=240),
                    Spacer(1, 8),
                ]))
            except Exception:
                pass

    doc.build(story)
    return output.getvalue()
