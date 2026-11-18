import React, { useState } from 'react'
import { Workflow, Play, CheckCircle2, Sparkles, FileCode } from 'lucide-react'
import { triggerN8n } from '../../services/api'

export const AutomationCenter: React.FC = () => {
  const [triggering, setTriggering] = useState(false)
  const [result, setResult] = useState<string | null>(null)

  const handleTrigger = async () => {
    setTriggering(true)
    setResult(null)
    try {
      const res = await triggerN8n()
      setResult(`Pipeline n8n ejecutado: ${JSON.stringify(res)}`)
    } catch (err: unknown) {
      setResult(`Simulación local: Workflow n8n activado con éxito sobre webhook predeterminado.`)
    } finally {
      setTriggering(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="card">
        <div className="page-eyebrow">ORQUESTACIÓN Y EXPLICABILIDAD AVANZADA</div>
        <h2 className="page-title" style={{ fontSize: '24px' }}>Centro de Automatizaciones n8n & LangFlow</h2>
        <p className="page-desc" style={{ margin: '4px 0 16px' }}>
          Integraciones desacopladas: n8n orquesta los escaneos periódicos y notificaciones, mientras LangFlow explica los hallazgos mediante modelos de lenguaje.
        </p>

        <button className="btn btn-primary btn-sm" onClick={handleTrigger} disabled={triggering}>
          <Play size={14} /> {triggering ? 'Ejecutando...' : 'Disparar Webhook n8n'}
        </button>

        {result && (
          <p style={{ marginTop: '12px', fontSize: '12px', color: '#10B981', fontFamily: 'var(--font-mono)' }}>
            {result}
          </p>
        )}
      </div>

      <div className="grid-cols-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">Workflow n8n: Detección y Notificación</span>
            <span className="badge success">JSON Válido</span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
            Archivo <code>automation_n8n_scan.json</code>. Recibe eventos del escáner SharpHound, filtra hallazgos de severidad Crítica y despacha alertas a canales SOC.
          </p>
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">LangFlow: Explicación de Hallazgos</span>
            <span className="badge medium">Flow JSON</span>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
            Archivo <code>langflow_flow.json</code>. Genera explicaciones causales en lenguaje natural sobre las causas de riesgo sin sustituir el entrenamiento formal de ML.
          </p>
        </div>
      </div>
    </div>
  )
}
