import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  API_BASE_URL,
  DashboardResponse,
  getDashboard,
  getHealth,
  HealthResponse,
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

const syntheticKpis: Kpi[] = [
  { label: 'Casos activos', value: '128', detail: 'en seguimiento', trend: '+8.4%', tone: 'cyan' },
  { label: 'Atención prioritaria', value: '24', detail: 'requieren revisión', trend: '-3.1%', tone: 'amber' },
  { label: 'Cobertura operativa', value: '87%', detail: 'de la capacidad', trend: '+5.8%', tone: 'green' },
  { label: 'Tiempo medio', value: '2.6 d', detail: 'hasta resolución', trend: '-12.0%', tone: 'violet' },
]

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null

const asText = (value: unknown, fallback: string) =>
  value === undefined || value === null || value === '' ? fallback : String(value)

const parseKpis = (payload?: DashboardResponse): Kpi[] => {
  const raw = payload?.kpis
  if (!Array.isArray(raw)) return syntheticKpis

  const parsed = raw
    .filter(isRecord)
    .map((item, index) => ({
      label: asText(item.label ?? item.name, syntheticKpis[index]?.label ?? `Indicador ${index + 1}`),
      value: asText(item.value, syntheticKpis[index]?.value ?? '—'),
      detail: asText(item.detail ?? item.description, 'dato reportado por API'),
      trend: asText(item.trend ?? item.change, 'sin variación'),
      tone: (['cyan', 'violet', 'amber', 'green'] as const)[index % 4],
    }))
  return parsed.length ? parsed.slice(0, 4) : syntheticKpis
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
  const usingSyntheticData = connection !== 'online' || !Array.isArray(dashboard?.kpis)
  const statusCopy = {
    loading: 'Comprobando integración…',
    online: 'API conectada',
    partial: 'Integración parcial',
    offline: 'Modo degradado',
  }[connection]
  const statusDescription = {
    loading: 'Consultando los servicios de CASO16',
    online: 'Salud y panel responden correctamente',
    partial: 'Un servicio responde; revisa los endpoints',
    offline: 'No fue posible contactar la API local',
  }[connection]

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark">C16</span>
          <div>
            <strong>CASO16</strong>
            <span className="brand-subtitle">control operativo</span>
          </div>
        </div>
        <div className="topbar-meta">
          <span className="environment-dot" /> Entorno local
          <span className="divider" />
          <span className="date-label">Panel de seguimiento</span>
        </div>
      </header>

      <main className="content">
        <section className="hero-grid">
          <div className="hero-copy">
            <p className="eyebrow">Vista general · CASO16</p>
            <h1>Señales claras para<br /><em>decidir a tiempo.</em></h1>
            <p className="hero-description">
              Un resumen operativo para orientar prioridades, capacidad y evolución de los casos en curso.
            </p>
            <div className="hero-actions">
              <button className="refresh-button" onClick={() => void loadData()} disabled={connection === 'loading'}>
                <span className={connection === 'loading' ? 'spin' : ''}>↻</span>
                {connection === 'loading' ? 'Actualizando…' : 'Actualizar datos'}
              </button>
              <span className="checked-at">
                {lastChecked ? `Última consulta ${lastChecked.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}` : 'Preparando consulta'}
              </span>
            </div>
          </div>

          <aside className={`integration-card ${connection}`}>
            <div className="card-heading">
              <span className="section-label">Estado de integración</span>
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

        {usingSyntheticData && (
          <div className="synthetic-banner" role="status">
            <span className="banner-icon">✦</span>
            <div>
              <strong>Datos sintéticos de referencia</strong>
              <span>La vista sigue disponible para explorar el shell. Se sustituirá al responder la API.</span>
            </div>
            <span className="banner-tag">DEMO</span>
          </div>
        )}

        <section className="metrics-section">
          <div className="section-title-row">
            <div>
              <p className="eyebrow">Indicadores principales</p>
              <h2>Ritmo de operación</h2>
            </div>
            <span className="data-source">{usingSyntheticData ? 'Referencia visual' : 'Datos en vivo'}</span>
          </div>
          <div className="kpi-grid">
            {kpis.map((kpi) => <KpiCard key={kpi.label} kpi={kpi} />)}
          </div>
        </section>

        <section className="insight-grid">
          <article className="insight-card spotlight-card">
            <div className="card-heading">
              <span className="section-label">Lectura rápida</span>
              <span className="sparkle">✦</span>
            </div>
            <h3>La operación mantiene una tendencia estable.</h3>
            <p>Prioriza los casos con mayor permanencia y conserva el pulso de cobertura en los próximos ciclos.</p>
            <div className="mini-chart" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /></div>
          </article>
          <article className="insight-card checklist-card">
            <div className="card-heading">
              <span className="section-label">Próximos pasos</span>
              <span className="step-count">02 / 03</span>
            </div>
            <ul className="checklist">
              <li className="done"><span>✓</span><div><strong>Revisar prioridades</strong><small>Clasificación inicial completada</small></div></li>
              <li><span>2</span><div><strong>Validar capacidad</strong><small>Contrastar con el equipo operativo</small></div></li>
              <li><span>3</span><div><strong>Actualizar seguimiento</strong><small>Registrar el próximo corte</small></div></li>
            </ul>
          </article>
        </section>
      </main>

      <footer className="footer"><span>CASO16</span><span>Shell frontend · Integración opcional</span></footer>
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
