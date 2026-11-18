import React from 'react'
import {
  ShieldAlert,
  Users,
  UserX,
  KeyRound,
  AlertTriangle,
  CheckCircle,
  Clock,
  Lock,
  ArrowUpRight,
  TrendingUp,
  FileSpreadsheet,
  Layers,
  ChevronRight,
  RefreshCw,
  Sparkles,
} from 'lucide-react'
import { DashboardResponse, DirectoryAccount, HealthResponse, NavItemKey } from '../../types'

interface SecurityOverviewProps {
  dashboard?: DashboardResponse | null
  health?: HealthResponse | null
  topAccounts: DirectoryAccount[]
  onSelectNav: (key: NavItemKey) => void
  onSelectAccount?: (account: DirectoryAccount) => void
  onExportReport: (format: 'pdf' | 'docx' | 'xlsx') => void
  onRefresh?: () => void
}

export const SecurityOverview: React.FC<SecurityOverviewProps> = ({
  dashboard,
  health,
  topAccounts,
  onSelectNav,
  onSelectAccount,
  onExportReport,
  onRefresh,
}) => {
  const totalAccounts = dashboard?.accounts ?? 113
  const inactiveAccounts = dashboard?.inactive ?? 81
  const excessivePrivs = dashboard?.excessive ?? 64
  const openFindings = dashboard?.open_findings ?? 269
  const svcNoExpiry = dashboard?.service_no_expiry ?? 17
  const totalRisk = dashboard?.risk_total ?? 6671

  return (
    <div className="security-overview-container" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* HERO BANNER EMPRESARIAL — LEGIBLE EN MODO CLARO Y OSCURO */}
      <div className="page-hero-banner">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '18px' }}>
          <div>
            <div className="page-eyebrow">MONITOREO DE IDENTIDADES Y PRIVILEGIOS · ACTIVE DIRECTORY</div>
            <h1 className="page-title">Security Overview</h1>
            <p className="page-desc">
              Monitoreo inteligente de identidades, privilegios y riesgos de ciberseguridad sobre dominios AD de SharpHound
              (PHANTOM.CORP, WRAITH.CORP, ESC1.LOCAL, GHOST.CORP).
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
            {onRefresh && (
              <button className="btn btn-secondary btn-sm" onClick={onRefresh} title="Sincronizar telemetría">
                <RefreshCw size={13} /> Sincronizar
              </button>
            )}
            <button className="btn btn-secondary btn-sm" onClick={() => onExportReport('pdf')}>
              <FileSpreadsheet size={13} /> Exportar PDF
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() => onExportReport('xlsx')}>
              <FileSpreadsheet size={13} /> Exportar Excel
            </button>
            <button className="btn btn-primary btn-sm" onClick={() => onSelectNav('ai-training-center')}>
              <Sparkles size={14} /> AI Training Center
            </button>
          </div>
        </div>
      </div>

      {/* 8 KPI CARDS ENTERPRISE CON FONDO UNIFORME Y CLICKEABLES */}
      <div className="grid-cols-4">
        {/* KPI 1 */}
        <div
          className="kpi-card-enterprise"
          onClick={() => onSelectNav('identities')}
          title="Ver inventario completo de identidades"
        >
          <div className="kpi-card-top">
            <span className="kpi-card-label">Cuentas Monitoreadas</span>
            <div className="kpi-card-icon-container">
              <Users size={17} />
            </div>
          </div>
          <div className="kpi-card-value">{totalAccounts}</div>
          <div className="kpi-card-subtext">
            <span>4 dominios AD</span>
            <span className="kpi-card-tag" style={{ color: 'var(--primary)' }}>SharpHound AD</span>
          </div>
        </div>

        {/* KPI 2 */}
        <div
          className="kpi-card-enterprise"
          onClick={() => onSelectNav('orphans')}
          title="Ver cuentas huérfanas inactivas"
        >
          <div className="kpi-card-top">
            <span className="kpi-card-label">Cuentas Inactivas (≥90d)</span>
            <div className="kpi-card-icon-container warning">
              <Clock size={17} />
            </div>
          </div>
          <div className="kpi-card-value">{inactiveAccounts}</div>
          <div className="kpi-card-subtext">
            <span>Regla R01 activa</span>
            <span className="kpi-card-tag" style={{ color: 'var(--warning)' }}>71.7% inventario</span>
          </div>
        </div>

        {/* KPI 3 */}
        <div
          className="kpi-card-enterprise"
          onClick={() => onSelectNav('findings')}
          title="Ver hallazgos de alto y crítico riesgo"
        >
          <div className="kpi-card-top">
            <span className="kpi-card-label">Riesgo Alto o Crítico</span>
            <div className="kpi-card-icon-container danger">
              <ShieldAlert size={17} />
            </div>
          </div>
          <div className="kpi-card-value">{excessivePrivs}</div>
          <div className="kpi-card-subtext">
            <span>Score ponderado ≥ 60</span>
            <span className="kpi-card-tag" style={{ color: 'var(--destructive)' }}>Prioridad SOC</span>
          </div>
        </div>

        {/* KPI 4 */}
        <div
          className="kpi-card-enterprise"
          onClick={() => onSelectNav('findings')}
          title="Ver todos los hallazgos abiertos"
        >
          <div className="kpi-card-top">
            <span className="kpi-card-label">Hallazgos Abiertos</span>
            <div className="kpi-card-icon-container warning">
              <AlertTriangle size={17} />
            </div>
          </div>
          <div className="kpi-card-value">{openFindings}</div>
          <div className="kpi-card-subtext">
            <span>Reglas R01–R06</span>
            <span className="kpi-card-tag" style={{ color: 'var(--warning)' }}>269 activos</span>
          </div>
        </div>

        {/* KPI 5 */}
        <div
          className="kpi-card-enterprise"
          onClick={() => onSelectNav('excessive-privs')}
          title="Ver cuentas de servicio sin expiración"
        >
          <div className="kpi-card-top">
            <span className="kpi-card-label">Servicios sin Expiración</span>
            <div className="kpi-card-icon-container danger">
              <Lock size={17} />
            </div>
          </div>
          <div className="kpi-card-value">{svcNoExpiry}</div>
          <div className="kpi-card-subtext">
            <span>Regla R04 (Clave eterna)</span>
            <span className="kpi-card-tag" style={{ color: 'var(--destructive)' }}>SPN sin rotación</span>
          </div>
        </div>

        {/* KPI 6 */}
        <div
          className="kpi-card-enterprise"
          onClick={() => onSelectNav('security-monitor')}
          title="Ver desglose del puntaje global"
        >
          <div className="kpi-card-top">
            <span className="kpi-card-label">Puntaje de Riesgo Acumulado</span>
            <div className="kpi-card-icon-container">
              <TrendingUp size={17} />
            </div>
          </div>
          <div className="kpi-card-value">{totalRisk.toLocaleString()}</div>
          <div className="kpi-card-subtext">
            <span>Severidad total</span>
            <span className="kpi-card-tag" style={{ color: 'var(--primary)' }}>Índice global</span>
          </div>
        </div>

        {/* KPI 7 */}
        <div
          className="kpi-card-enterprise"
          onClick={() => onSelectNav('excessive-privs')}
          title="Ver administradores sin justificación"
        >
          <div className="kpi-card-top">
            <span className="kpi-card-label">Admins sin Justificación</span>
            <div className="kpi-card-icon-container warning">
              <KeyRound size={17} />
            </div>
          </div>
          <div className="kpi-card-value">32</div>
          <div className="kpi-card-subtext">
            <span>Regla R02 activa</span>
            <span className="kpi-card-tag" style={{ color: 'var(--warning)' }}>Revisión requerida</span>
          </div>
        </div>

        {/* KPI 8 */}
        <div
          className="kpi-card-enterprise"
          onClick={() => onSelectNav('policies')}
          title="Ver marco de control y políticas"
        >
          <div className="kpi-card-top">
            <span className="kpi-card-label">Evaluación Marco ISO 27001</span>
            <div className="kpi-card-icon-container success">
              <CheckCircle size={17} />
            </div>
          </div>
          <div className="kpi-card-value">A.8.2</div>
          <div className="kpi-card-subtext">
            <span>Control de privilegios</span>
            <span className="kpi-card-tag" style={{ color: 'var(--success)' }}>Referencia analítica</span>
          </div>
        </div>
      </div>

      {/* GRÁFICOS VISUALES */}
      <div className="grid-cols-2">
        {/* Distribución de Severidad */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Distribución de Hallazgos por Severidad</span>
            <span className="badge medium">269 Total</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginTop: '12px' }}>
            {[
              { label: 'Crítico', count: 44, pct: 16.4, color: 'var(--destructive)' },
              { label: 'Alto', count: 107, pct: 39.8, color: 'var(--warning)' },
              { label: 'Medio', count: 118, pct: 43.8, color: 'var(--secondary)' },
            ].map((sev) => (
              <div key={sev.label} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                  <span style={{ fontWeight: 600, color: sev.color }}>{sev.label}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--muted-foreground)', fontSize: '12px' }}>
                    {sev.count} ({sev.pct}%)
                  </span>
                </div>
                <div style={{ width: '100%', height: '8px', background: 'var(--surface-elevated)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${sev.pct}%`, height: '100%', background: sev.color, borderRadius: '4px' }} />
                </div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: '12px', color: 'var(--muted-foreground)', marginTop: '18px', lineHeight: 1.5 }}>
            Los hallazgos Críticos corresponden a inconsistencias de privilegios normativos (R05) y combinaciones de alto riesgo sin revisión formal (R06).
          </p>
        </div>

        {/* Distribución por Regla R01 a R06 */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Incidencia por Regla Determinista (R01–R06)</span>
            <span className="badge high">SharpHound AD</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '12px' }}>
            {[
              { id: 'R01', name: 'Inactividad prolongada (≥90d)', count: 81, max: 81, color: 'var(--primary)' },
              { id: 'R06', name: 'Riesgo alto sin revisión', count: 58, max: 81, color: 'var(--destructive)' },
              { id: 'R05', name: 'Privilegios inconsistentes', count: 44, max: 81, color: '#C026D3' },
              { id: 'R03', name: 'Admin duplicado redundante', count: 37, max: 81, color: 'var(--warning)' },
              { id: 'R02', name: 'Admin sin justificación', count: 32, max: 81, color: 'var(--secondary)' },
              { id: 'R04', name: 'Servicio con clave eterna', count: 17, max: 81, color: 'var(--success)' },
            ].map((rule) => (
              <div key={rule.id} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span className="badge" style={{ minWidth: '45px', textAlign: 'center', background: 'var(--surface-elevated)', color: rule.color, border: '1px solid var(--border)' }}>
                  {rule.id}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '3px' }}>
                    <span style={{ color: 'var(--foreground)', fontSize: '12px' }}>{rule.name}</span>
                    <strong style={{ fontFamily: 'var(--font-mono)', color: rule.color }}>{rule.count}</strong>
                  </div>
                  <div style={{ width: '100%', height: '6px', background: 'var(--surface-elevated)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${(rule.count / rule.max) * 100}%`, height: '100%', background: rule.color }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* TABLA DE IDENTIDADES PRIORIZADAS POR RIESGO */}
      <div className="card">
        <div className="card-header">
          <div>
            <span className="card-title">Top Identidades Críticas con Mayor Puntuación de Riesgo</span>
            <p style={{ fontSize: '12px', color: 'var(--muted-foreground)', margin: '4px 0 0' }}>
              Cuentas que requieren atención prioritaria en el SOC debido a acumulación de violaciones normativas.
            </p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => onSelectNav('identities')}>
            Ver todas ({totalAccounts}) <ChevronRight size={14} />
          </button>
        </div>

        <div className="data-table-container" style={{ marginTop: '12px' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Identidad</th>
                <th>Dominio AD</th>
                <th>Tipo</th>
                <th>Privilegios</th>
                <th>Inactividad</th>
                <th>Score de Riesgo</th>
                <th>Severidad</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {topAccounts.slice(0, 7).map((acc) => (
                <tr key={acc.id}>
                  <td>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <strong style={{ color: 'var(--foreground)' }}>{acc.username}</strong>
                      <span style={{ fontSize: '11px', color: 'var(--muted-foreground)', fontFamily: 'var(--font-mono)' }}>
                        {acc.external_id}
                      </span>
                    </div>
                  </td>
                  <td>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                      {acc.source.replace('SharpHound AD (', '').replace(')', '')}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${acc.account_type === 'service' ? 'medium' : 'low'}`}>
                      {acc.account_type}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: '12px', color: acc.is_admin ? 'var(--destructive)' : 'var(--muted-foreground)', fontWeight: acc.is_admin ? 600 : 400 }}>
                      {acc.is_admin ? '🛡️ Domain Admin' : 'Domain User'}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                      {acc.last_activity ? acc.last_activity : 'Sin logon registrado'}
                    </span>
                  </td>
                  <td>
                    <strong style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '13px',
                      color: acc.risk_score >= 80 ? 'var(--destructive)' : acc.risk_score >= 60 ? 'var(--warning)' : 'var(--primary)'
                    }}>
                      {acc.risk_score} / 100
                    </strong>
                  </td>
                  <td>
                    <span className={`badge ${acc.risk_score >= 80 ? 'critical' : acc.risk_score >= 60 ? 'high' : 'medium'}`}>
                      {acc.risk_score >= 80 ? 'Crítico' : acc.risk_score >= 60 ? 'Alto' : 'Medio'}
                    </span>
                  </td>
                  <td>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => onSelectAccount && onSelectAccount(acc)}
                    >
                      Inspeccionar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
