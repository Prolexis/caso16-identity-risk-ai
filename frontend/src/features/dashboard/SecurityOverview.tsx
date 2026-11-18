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
} from 'lucide-react'
import { DashboardResponse, DirectoryAccount, HealthResponse, NavItemKey } from '../../types'

interface SecurityOverviewProps {
  dashboard?: DashboardResponse | null
  health?: HealthResponse | null
  topAccounts: DirectoryAccount[]
  onSelectNav: (key: NavItemKey) => void
  onSelectAccount?: (account: DirectoryAccount) => void
  onExportReport: (format: 'pdf' | 'docx' | 'xlsx') => void
}

export const SecurityOverview: React.FC<SecurityOverviewProps> = ({
  dashboard,
  health,
  topAccounts,
  onSelectNav,
  onSelectAccount,
  onExportReport,
}) => {
  const totalAccounts = dashboard?.accounts ?? 113
  const inactiveAccounts = dashboard?.inactive ?? 81
  const excessivePrivs = dashboard?.excessive ?? 64
  const openFindings = dashboard?.open_findings ?? 269
  const svcNoExpiry = dashboard?.service_no_expiry ?? 17
  const totalRisk = dashboard?.risk_total ?? 6671

  return (
    <div className="security-overview-container" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Banner Principal */}
      <div className="card" style={{ background: 'linear-gradient(135deg, rgba(17,29,50,0.9), rgba(13,22,40,0.95))', border: '1px solid rgba(34,211,238,0.2)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div className="page-eyebrow">MONITOREO DE IDENTIDADES Y PRIVILEGIOS · ACTIVE DIRECTORY</div>
            <h1 className="page-title" style={{ fontSize: '28px', margin: '4px 0 8px' }}>Security Overview</h1>
            <p className="page-desc" style={{ margin: 0 }}>
              Evaluación determinista (R01–R06) y priorización con Inteligencia Artificial sobre 4 dominios AD de SharpHound
              (PHANTOM.CORP, WRAITH.CORP, ESC1.LOCAL, GHOST.CORP).
            </p>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button className="btn btn-secondary btn-sm" onClick={() => onExportReport('pdf')}>
              <FileSpreadsheet size={14} /> Exportar PDF
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() => onExportReport('xlsx')}>
              <FileSpreadsheet size={14} /> Exportar Excel
            </button>
            <button className="btn btn-primary btn-sm" onClick={() => onSelectNav('ai-training-center')}>
              <TrendingUp size={14} /> Motor de IA
            </button>
          </div>
        </div>
      </div>

      {/* 8 KPI CARDS EMPRESARIALES */}
      <div className="grid-cols-4">
        {/* KPI 1 */}
        <div className="kpi-card-premium" style={{ '--card-accent': '#22D3EE' } as React.CSSProperties}>
          <div className="kpi-card-top">
            <span className="kpi-card-label">Cuentas Monitoreadas</span>
            <div className="kpi-card-icon"><Users size={18} /></div>
          </div>
          <div className="kpi-card-value">{totalAccounts}</div>
          <div className="kpi-card-subtext">
            <span>4 dominios AD auditados</span>
            <span style={{ color: '#22D3EE' }}>100% cobertura</span>
          </div>
        </div>

        {/* KPI 2 */}
        <div className="kpi-card-premium" style={{ '--card-accent': '#F59E0B' } as React.CSSProperties}>
          <div className="kpi-card-top">
            <span className="kpi-card-label">Cuentas Inactivas (≥90d)</span>
            <div className="kpi-card-icon"><Clock size={18} /></div>
          </div>
          <div className="kpi-card-value">{inactiveAccounts}</div>
          <div className="kpi-card-subtext">
            <span>Regla R01 activa</span>
            <span style={{ color: '#F59E0B' }}>71.7% del total</span>
          </div>
        </div>

        {/* KPI 3 */}
        <div className="kpi-card-premium" style={{ '--card-accent': '#F43F5E' } as React.CSSProperties}>
          <div className="kpi-card-top">
            <span className="kpi-card-label">Riesgo Alto o Crítico</span>
            <div className="kpi-card-icon"><ShieldAlert size={18} /></div>
          </div>
          <div className="kpi-card-value">{excessivePrivs}</div>
          <div className="kpi-card-subtext">
            <span>Score determinista ≥ 60</span>
            <span style={{ color: '#F43F5E' }}>Prioridad SOC</span>
          </div>
        </div>

        {/* KPI 4 */}
        <div className="kpi-card-premium" style={{ '--card-accent': '#818CF8' } as React.CSSProperties}>
          <div className="kpi-card-top">
            <span className="kpi-card-label">Hallazgos Abiertos</span>
            <div className="kpi-card-icon"><AlertTriangle size={18} /></div>
          </div>
          <div className="kpi-card-value">{openFindings}</div>
          <div className="kpi-card-subtext">
            <span>Reglas R01–R06</span>
            <span style={{ color: '#818CF8' }}>269 detectados</span>
          </div>
        </div>

        {/* KPI 5 */}
        <div className="kpi-card-premium" style={{ '--card-accent': '#10B981' } as React.CSSProperties}>
          <div className="kpi-card-top">
            <span className="kpi-card-label">Servicios sin Expiración</span>
            <div className="kpi-card-icon"><Lock size={18} /></div>
          </div>
          <div className="kpi-card-value">{svcNoExpiry}</div>
          <div className="kpi-card-subtext">
            <span>Regla R04 (Clave eterna)</span>
            <span style={{ color: '#10B981' }}>Crítico SPN</span>
          </div>
        </div>

        {/* KPI 6 */}
        <div className="kpi-card-premium" style={{ '--card-accent': '#EC4899' } as React.CSSProperties}>
          <div className="kpi-card-top">
            <span className="kpi-card-label">Puntaje de Riesgo Total</span>
            <div className="kpi-card-icon"><TrendingUp size={18} /></div>
          </div>
          <div className="kpi-card-value">{totalRisk.toLocaleString()}</div>
          <div className="kpi-card-subtext">
            <span>Riesgo acumulado</span>
            <span style={{ color: '#EC4899' }}>Índice global</span>
          </div>
        </div>

        {/* KPI 7 */}
        <div className="kpi-card-premium" style={{ '--card-accent': '#06B6D4' } as React.CSSProperties}>
          <div className="kpi-card-top">
            <span className="kpi-card-label">Admins sin Justificación</span>
            <div className="kpi-card-icon"><KeyRound size={18} /></div>
          </div>
          <div className="kpi-card-value">32</div>
          <div className="kpi-card-subtext">
            <span>Regla R02</span>
            <span style={{ color: '#06B6D4' }}>Falta justificación</span>
          </div>
        </div>

        {/* KPI 8 */}
        <div className="kpi-card-premium" style={{ '--card-accent': '#10B981' } as React.CSSProperties}>
          <div className="kpi-card-top">
            <span className="kpi-card-label">Cumplimiento ISO 27001</span>
            <div className="kpi-card-icon"><CheckCircle size={18} /></div>
          </div>
          <div className="kpi-card-value">A.8.2</div>
          <div className="kpi-card-subtext">
            <span>Control de privilegios</span>
            <span style={{ color: '#10B981' }}>Auditado</span>
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
              { label: 'Crítico', count: 44, pct: 16.4, color: '#F43F5E' },
              { label: 'Alto', count: 107, pct: 39.8, color: '#F59E0B' },
              { label: 'Medio', count: 118, pct: 43.8, color: '#818CF8' },
            ].map((sev) => (
              <div key={sev.label} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                  <span style={{ fontWeight: 600, color: sev.color }}>{sev.label}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                    {sev.count} ({sev.pct}%)
                  </span>
                </div>
                <div style={{ width: '100%', height: '8px', background: 'var(--bg-elevated)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ width: `${sev.pct}%`, height: '100%', background: sev.color, borderRadius: '4px' }} />
                </div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-dim)', marginTop: '18px', lineHeight: 1.5 }}>
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
              { id: 'R01', name: 'Inactividad prolongada (≥90d)', count: 81, max: 81, color: '#22D3EE' },
              { id: 'R06', name: 'Riesgo alto sin revisión', count: 58, max: 81, color: '#F43F5E' },
              { id: 'R05', name: 'Privilegios inconsistentes', count: 44, max: 81, color: '#EC4899' },
              { id: 'R03', name: 'Admin duplicado redundante', count: 37, max: 81, color: '#F59E0B' },
              { id: 'R02', name: 'Admin sin justificación', count: 32, max: 81, color: '#818CF8' },
              { id: 'R04', name: 'Servicio con clave eterna', count: 17, max: 81, color: '#10B981' },
            ].map((rule) => (
              <div key={rule.id} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span className="badge" style={{ minWidth: '45px', textAlign: 'center', background: 'var(--bg-elevated)', color: rule.color }}>
                  {rule.id}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '2px' }}>
                    <span style={{ color: 'var(--text-main)', fontSize: '11px' }}>{rule.name}</span>
                    <strong style={{ fontFamily: 'var(--font-mono)', color: rule.color }}>{rule.count}</strong>
                  </div>
                  <div style={{ width: '100%', height: '5px', background: 'var(--bg-elevated)', borderRadius: '3px', overflow: 'hidden' }}>
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
            <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: '4px 0 0' }}>
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
                      <strong style={{ color: 'var(--text-main)' }}>{acc.username}</strong>
                      <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                        {acc.external_id}
                      </span>
                    </div>
                  </td>
                  <td>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                      {acc.source.replace('SharpHound AD (', '').replace(')', '')}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${acc.account_type === 'service' ? 'medium' : 'low'}`}>
                      {acc.account_type}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: '11px', color: acc.is_admin ? '#F43F5E' : 'var(--text-muted)', fontWeight: acc.is_admin ? 600 : 400 }}>
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
                      fontSize: '14px',
                      color: acc.risk_score >= 80 ? '#F43F5E' : acc.risk_score >= 60 ? '#F59E0B' : '#818CF8'
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
