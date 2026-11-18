import React, { useState } from 'react'
import {
  FileSpreadsheet,
  Download,
  FileText,
  Shield,
  Cpu,
  CheckCircle,
  FileCheck,
} from 'lucide-react'
import {
  getGeneralReportDownloadUrl,
  getTrainingReportDownloadUrl,
} from '../../services/api'
import { ExperimentJob } from '../../types'

interface ReportCenterProps {
  jobs: ExperimentJob[]
}

export const ReportCenter: React.FC<ReportCenterProps> = ({ jobs }) => {
  const [selectedJobId, setSelectedJobId] = useState<string>(jobs.length > 0 ? jobs[0].job_id : '')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="card">
        <div className="page-eyebrow">CENTRO DE INFORMES EJECUTIVOS Y DE CUMPLIMIENTO</div>
        <h2 className="page-title" style={{ fontSize: '24px' }}>Centro de Reportes y Evidencias de Auditoría</h2>
        <p className="page-desc" style={{ margin: '4px 0 0' }}>
          Generación y descarga de informes técnicos en formatos estándar (PDF, Word .docx y Excel .xlsx) con trazabilidad SHA-256 para auditoría externa e ISO 27001.
        </p>
      </div>

      <div className="grid-cols-2">
        {/* REPORTE GENERAL SOC */}
        <div className="card" style={{ borderTop: '3px solid var(--color-primary)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <div className="kpi-card-icon" style={{ background: 'rgba(34,211,238,0.15)', color: '#22D3EE' }}>
              <Shield size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '16px', margin: 0, color: 'var(--text-main)' }}>
                Reporte Ejecutivo de Riesgo e Identidades (SOC)
              </h3>
              <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                Reglas R01–R06 · 113 cuentas · 269 hallazgos
              </span>
            </div>
          </div>

          <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: '20px' }}>
            Consolida el inventario completo de cuentas de Active Directory, distribución de severidades, desglose de cuentas huérfanas y administradores sin justificación.
          </p>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <a
              href={getGeneralReportDownloadUrl('pdf')}
              target="_blank"
              rel="noreferrer"
              className="btn btn-sm"
              style={{ background: '#ef4444', color: '#fff' }}
            >
              <Download size={14} /> Descargar PDF
            </a>
            <a
              href={getGeneralReportDownloadUrl('docx')}
              target="_blank"
              rel="noreferrer"
              className="btn btn-sm"
              style={{ background: '#2563eb', color: '#fff' }}
            >
              <Download size={14} /> Descargar Word
            </a>
            <a
              href={getGeneralReportDownloadUrl('xlsx')}
              target="_blank"
              rel="noreferrer"
              className="btn btn-sm"
              style={{ background: '#10b981', color: '#fff' }}
            >
              <Download size={14} /> Descargar Excel
            </a>
          </div>
        </div>

        {/* REPORTE DE ENTRENAMIENTO IA */}
        <div className="card" style={{ borderTop: '3px solid var(--color-secondary)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
            <div className="kpi-card-icon" style={{ background: 'rgba(129,140,248,0.15)', color: '#818CF8' }}>
              <Cpu size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '16px', margin: 0, color: 'var(--text-main)' }}>
                Reporte de Modelos de Inteligencia Artificial (MLOps)
              </h3>
              <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                Evaluación M1, M2, M3 · Optuna TPE · Blind Test 15%
              </span>
            </div>
          </div>

          <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.6, marginBottom: '14px' }}>
            Detalla la metodología EDA, preprocesamiento antifuga, hiperparámetros optimizados, matrices de confusión y tabla comparativa M1 vs M2.
          </p>

          <div style={{ marginBottom: '14px' }}>
            <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
              Seleccionar corrida de experimento:
            </label>
            <select
              className="select-filter"
              value={selectedJobId}
              onChange={(e) => setSelectedJobId(e.target.value)}
              style={{ width: '100%' }}
            >
              {jobs.map((j) => (
                <option key={j.job_id} value={j.job_id}>
                  {j.job_id} — {j.status} ({new Date(j.created_at).toLocaleTimeString('es-PE')})
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <a
              href={selectedJobId ? getTrainingReportDownloadUrl(selectedJobId, 'pdf') : '#'}
              target="_blank"
              rel="noreferrer"
              className="btn btn-sm"
              style={{ background: '#ef4444', color: '#fff', opacity: selectedJobId ? 1 : 0.5 }}
            >
              <Download size={14} /> PDF de IA
            </a>
            <a
              href={selectedJobId ? getTrainingReportDownloadUrl(selectedJobId, 'docx') : '#'}
              target="_blank"
              rel="noreferrer"
              className="btn btn-sm"
              style={{ background: '#2563eb', color: '#fff', opacity: selectedJobId ? 1 : 0.5 }}
            >
              <Download size={14} /> Word de IA
            </a>
            <a
              href={selectedJobId ? getTrainingReportDownloadUrl(selectedJobId, 'xlsx') : '#'}
              target="_blank"
              rel="noreferrer"
              className="btn btn-sm"
              style={{ background: '#10b981', color: '#fff', opacity: selectedJobId ? 1 : 0.5 }}
            >
              <Download size={14} /> Excel de IA
            </a>
          </div>
        </div>
      </div>
    </div>
  )
}
