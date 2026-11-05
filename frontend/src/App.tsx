import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  API_BASE_URL,
  DashboardResponse,
  getDashboard,
  getHealth,
} from './api'

type ConnectionState = 'loading' | 'online' | 'partial' | 'offline'
type EndpointState = 'loading' | 'ok' | 'error'

type Kpi = {
  label: string
  value: string
  detail: string
  trend: string
  tone: 'cyan' | 'violet' | 'amber' | 'green'
}

type Endpoint = {
  name: string
  path: string
  state: EndpointState
}

const defaultKpis: Kpi[] = [
  { label: 'Cuentas inventariadas', value: '113', detail: '4 dominios AD (SharpHound)', trend: '100% auditado', tone: 'cyan' },
  { label: 'Inactivas / huérfanas', value: '81', detail: 'Regla R01 (≥90d o lastLogon=0)', trend: '71.7% del total', tone: 'amber' },
  { label: 'Riesgo alto o crítico', value: '64', detail: 'Score determinista ≥ 60', trend: 'Prioridad SOC', tone: 'violet' },
  { label: 'Hallazgos abiertos', value: '269', detail: '44 Críticos · 107 Altos · 118 Medios', trend: 'R01–R06 activos', tone: 'green' },
]

const parseKpis = (payload?: DashboardResponse): Kpi[] => {
  if (!payload || typeof payload.accounts !== 'number') return defaultKpis
  return [
    {
      label: 'Cuentas inventariadas',
      value: String(payload.accounts),
      detail: '4 dominios AD (SharpHound)',
      trend: `Riesgo total: ${payload.risk_total ?? 6671}`,
      tone: 'cyan',
    },
    {
      label: 'Inactivas / huérfanas',
      value: String(payload.inactive ?? 81),
      detail: 'Regla R01 (≥90 días)',
      trend: `${payload.service_no_expiry ?? 17} svc sin expiración`,
      tone: 'amber',
    },
    {
      label: 'Riesgo alto o crítico',
      value: String(payload.excessive ?? 64),
      detail: 'Score determinista ≥ 60',
      trend: 'Control ISO 27001 A.8.2',
      tone: 'violet',
    },
    {
      label: 'Hallazgos abiertos',
      value: String(payload.open_findings ?? 269),
      detail: `${payload.closed_findings ?? 0} cerrados`,
      trend: 'R01–R06 activos',
      tone: 'green',
    },
  ]
}

function App() {
  const [connection, setConnection] = useState<ConnectionState>('loading')
  const [healthState, setHealthState] = useState<EndpointState>('loading')
  const [dashboardState, setDashboardState] = useState<EndpointState>('loading')
  const [dashboard, setDashboard] = useState<DashboardResponse>()
  const [lastChecked, setLastChecked] = useState<Date>()

  const loadData = useCallback(async () => {
    setConnection('loading')
    setHealthState('loading')
    setDashboardState('loading')

    const [healthResult, dashboardResult] = await Promise.allSettled([getHealth(), getDashboard()])
    const healthOk = healthResult.status === 'fulfilled'
    const dashboardOk = dashboardResult.status === 'fulfilled'
    setHealthState(healthOk ? 'ok' : 'error')
    setDashboardState(dashboardOk ? 'ok' : 'error')
    if (dashboardOk) setDashboard(dashboardResult.value)
    setConnection(healthOk && dashboardOk ? 'online' : healthOk || dashboardOk ? 'partial' : 'offline')
    setLastChecked(new Date())
  }, [])

  useEffect(() => {
    void loadData()
  }, [loadData])

  const kpis = useMemo(() => parseKpis(dashboard), [dashboard])
  const usingFallback = connection !== 'online'
  const statusCopy = {
    loading: 'Comprobando integración…',
    online: 'API conectada en vivo',
    partial: 'Integración parcial',
    offline: 'Snapshot local SharpHound',
  }[connection]
  const statusDescription = {
    loading: 'Consultando los servicios de CASO16',
    online: 'PostgreSQL y motor R01–R06 responden correctamente',
    partial: 'Un servicio responde; revisa los endpoints',
    offline: 'Mostrando snapshot verificado del dataset público SharpHound AD',
  }[connection]

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark">C16</span>
          <div>
            <strong>CASO16 · ORPHANHUNTER</strong>
            <span className="brand-subtitle">Identity Risk AI · SharpHound AD</span>
          </div>
        </div>
        <div className="topbar-meta">
          <span className="environment-dot" /> 4 Dominios AD Auditados
          <span className="divider" />
          <span className="date-label">ISO/IEC 27001 A.8.2</span>
        </div>
      </header>

      <main className="content">
        <section className="hero-grid">
          <div className="hero-copy">
            <p className="eyebrow">Cazador de Cuentas Huérfanas y Privilegios Excesivos</p>
            <h1>Visibilidad total sobre<br /><em>identidades críticas.</em></h1>
            <p className="hero-description">
              Evaluación determinista (R01–R06) ejecutada sobre el dataset público de telemetría Active Directory SharpHound / BloodHound (PHANTOM.CORP, WRAITH.CORP, ESC1.LOCAL y GHOST.CORP).
            </p>
            <div className="hero-actions">
              <button className="refresh-button" onClick={() => void loadData()} disabled={connection === 'loading'}>
                <span className={connection === 'loading' ? 'spin' : ''}>↻</span>
                {connection === 'loading' ? 'Sincronizando…' : 'Sincronizar métricas'}
              </button>
              <span className="checked-at">
                {lastChecked ? `Última consulta ${lastChecked.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}` : 'Preparando consulta'}
              </span>
            </div>
          </div>

          <aside className={`integration-card ${connection}`}>
            <div className="card-heading">
              <span className="section-label">Estado del Backend SOC</span>
              <span className="status-pulse" />
            </div>
            <div className="integration-status">{statusCopy}</div>
            <p>{statusDescription}</p>
            <div className="endpoint-summary">
              <EndpointRow name="Health check" path="/health" state={healthState} />
              <EndpointRow name="Dashboard" path="/dashboard" state={dashboardState} />
            </div>
            <code className="api-origin">{API_BASE_URL}</code>
          </aside>
        </section>

        <section className="metrics-section">
          <div className="section-title-row">
            <div>
              <p className="eyebrow">Resultados Reales · SharpHound Public AD Dataset</p>
              <h2>Indicadores de Exposición de Identidad</h2>
            </div>
            <span className="data-source">{usingFallback ? 'Snapshot Dataset Público' : 'API FastAPI + PostgreSQL en vivo'}</span>
          </div>
          <div className="kpi-grid">
            {kpis.map((kpi) => <KpiCard key={kpi.label} kpi={kpi} />)}
          </div>
        </section>

        <section className="insight-grid">
          <article className="insight-card spotlight-card">
            <div className="card-heading">
              <span className="section-label">Distribución por Regla (269 Hallazgos)</span>
              <span className="sparkle">✦</span>
            </div>
            <h3>Concentración en inactividad (R01) y privilegios fuera de política (R05).</h3>
            <p>R01: 81 · R06: 58 · R05: 44 · R03: 37 · R02: 32 · R04: 17 hallazgos detectados en las 113 cuentas.</p>
            <div className="mini-chart" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /></div>
          </article>
          <article className="insight-card checklist-card">
            <div className="card-heading">
              <span className="section-label">Cobertura de Auditoría</span>
              <span className="step-count">03 / 03</span>
            </div>
            <ul className="checklist">
              <li className="done"><span>✓</span><div><strong>Ingesta SharpHound AD</strong><small>113 cuentas y membresías LDAP procesadas</small></div></li>
              <li className="done"><span>✓</span><div><strong>Evaluación Determinista R01–R06</strong><small>117 hallazgos confirmados · 152 potenciales</small></div></li>
              <li className="done"><span>✓</span><div><strong>Reportes Ejecutivos y Bitácora</strong><small>Exportación XLSX, DOCX y PDF habilitada</small></div></li>
            </ul>
          </article>
        </section>
      </main>

      <footer className="footer"><span>CASO16 · ORPHANHUNTER</span><span>Dataset Público SharpHound/BloodHound AD · Licencia MIT</span></footer>
    </div>
  )
}

function EndpointRow({ name, path, state }: Endpoint) {
  const label = state === 'loading' ? 'consultando' : state === 'ok' ? 'operativo' : 'sin respuesta'
  return <div className="endpoint-row"><div><span className={`endpoint-dot ${state}`} /> <strong>{name}</strong></div><span><code>{path}</code> · {label}</span></div>
}

function KpiCard({ kpi }: { kpi: Kpi }) {
  return <article className={`kpi-card ${kpi.tone}`}><div className="kpi-topline"><span>{kpi.label}</span><span className="kpi-arrow">↗</span></div><strong className="kpi-value">{kpi.value}</strong><div className="kpi-footer"><span>{kpi.detail}</span><b>{kpi.trend}</b></div></article>
}

export default App
