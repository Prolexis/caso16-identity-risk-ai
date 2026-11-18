import React, { useState, useMemo } from 'react'
import {
  AlertTriangle,
  Search,
  Filter,
  CheckCircle,
  Clock,
  Shield,
  BrainCircuit,
  Ticket,
  X,
} from 'lucide-react'
import { SecurityFinding } from '../../types'
import { explainFindingAi, updateFindingStatus, createTicket } from '../../services/api'

interface FindingsManagementProps {
  findings: SecurityFinding[]
  onRefresh: () => void
}

export const FindingsManagement: React.FC<FindingsManagementProps> = ({ findings, onRefresh }) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [severityFilter, setSeverityFilter] = useState('all')
  const [ruleFilter, setRuleFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')

  const [selectedFinding, setSelectedFinding] = useState<SecurityFinding | null>(null)
  const [explanation, setExplanation] = useState<string | null>(null)
  const [explaining, setExplaining] = useState(false)
  const [ticketSuccess, setTicketSuccess] = useState<string | null>(null)

  const filteredFindings = useMemo(() => {
    return findings.filter((f) => {
      if (severityFilter !== 'all' && f.severity !== severityFilter) return false
      if (ruleFilter !== 'all' && f.rule_id !== ruleFilter) return false
      if (statusFilter !== 'all' && f.status !== statusFilter) return false
      if (searchTerm) {
        const q = searchTerm.toLowerCase()
        return (
          f.title.toLowerCase().includes(q) ||
          f.rule_id.toLowerCase().includes(q) ||
          f.rationale.toLowerCase().includes(q) ||
          f.evidence.toLowerCase().includes(q)
        )
      }
      return true
    })
  }, [findings, severityFilter, ruleFilter, statusFilter, searchTerm])

  const handleOpenFinding = async (f: SecurityFinding) => {
    setSelectedFinding(f)
    setExplanation(null)
    setTicketSuccess(null)
  }

  const handleExplain = async () => {
    if (!selectedFinding) return
    setExplaining(true)
    try {
      const res = await explainFindingAi(selectedFinding.id)
      setExplanation(
        (res.explanation as string) ||
        (res.heuristic as string) ||
        'Explicación determinista: El hallazgo fue detectado por coincidencia matemática de atributos de cuenta contra la política de gobierno de identidades.'
      )
    } catch (err: unknown) {
      setExplanation(`Explicación heurística: Hallazgo verificado por motor normativo R01–R06.`)
    } finally {
      setExplaining(false)
    }
  }

  const handleCreateRemediationTicket = async () => {
    if (!selectedFinding) return
    try {
      const res = await createTicket({
        finding_id: selectedFinding.id,
        title: `Remediación: ${selectedFinding.title}`,
        description: `Hallazgo ${selectedFinding.rule_id} con severidad ${selectedFinding.severity}. Rationale: ${selectedFinding.rationale}. Evidencia: ${selectedFinding.evidence}`,
        priority: selectedFinding.severity === 'Crítico' ? 'Crítica' : 'Alta',
        sla_days: selectedFinding.severity === 'Crítico' ? 3 : 7,
      })
      setTicketSuccess(`Ticket ${res.ticket_id} creado con SLA asignado.`)
      onRefresh()
    } catch (err: unknown) {
      setTicketSuccess(`Error: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div className="page-eyebrow">DETECCIÓN DETERMINISTA R01–R06</div>
            <h2 className="page-title" style={{ fontSize: '24px' }}>Gestión de Hallazgos de Seguridad</h2>
            <p className="page-desc" style={{ margin: '4px 0 0' }}>
              Mostrando {filteredFindings.length} de {findings.length} hallazgos normativos identificados en el inventario.
            </p>
          </div>
        </div>

        {/* Filtros */}
        <div className="filter-bar">
          <div className="search-input-wrap">
            <Search size={14} />
            <input
              type="text"
              className="search-input"
              placeholder="Buscar por regla, título o evidencia..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <select
            className="select-filter"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="all">Todas las Severidades</option>
            <option value="Crítico">Crítico</option>
            <option value="Alto">Alto</option>
            <option value="Medio">Medio</option>
          </select>

          <select
            className="select-filter"
            value={ruleFilter}
            onChange={(e) => setRuleFilter(e.target.value)}
          >
            <option value="all">Todas las Reglas (R01–R06)</option>
            <option value="R01">R01: Inactividad Prolongada</option>
            <option value="R02">R02: Admin sin Justificación</option>
            <option value="R03">R03: Admin Duplicado</option>
            <option value="R04">R04: Servicio Clave Eterna</option>
            <option value="R05">R05: Privilegios Inconsistentes</option>
            <option value="R06">R06: Riesgo Alto sin Revisión</option>
          </select>

          <select
            className="select-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">Todos los Estados</option>
            <option value="Detectado">Detectado</option>
            <option value="En revisión">En revisión</option>
            <option value="Remediado">Remediado</option>
          </select>
        </div>

        {/* Tabla */}
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Regla</th>
                <th>Título del Hallazgo</th>
                <th>Severidad</th>
                <th>Estado</th>
                <th>Score</th>
                <th>Responsable</th>
                <th>Fecha Detección</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {filteredFindings.map((f) => (
                <tr key={f.id}>
                  <td>
                    <span className="badge" style={{ background: 'var(--bg-elevated)', color: 'var(--color-primary)' }}>
                      {f.rule_id}
                    </span>
                  </td>
                  <td>
                    <strong style={{ color: 'var(--text-main)', fontSize: '13px' }}>{f.title}</strong>
                  </td>
                  <td>
                    <span className={`badge ${f.severity === 'Crítico' ? 'critical' : f.severity === 'Alto' ? 'high' : 'medium'}`}>
                      {f.severity}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${f.status === 'Remediado' ? 'success' : 'low'}`}>
                      {f.status}
                    </span>
                  </td>
                  <td>
                    <strong style={{ fontFamily: 'var(--font-mono)' }}>{f.risk_score}</strong>
                  </td>
                  <td>
                    <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                      {f.owner || 'Sin asignar'}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                      {new Date(f.created_at).toLocaleDateString('es-PE')}
                    </span>
                  </td>
                  <td>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleOpenFinding(f)}
                    >
                      Investigar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* DRAWER DETALLE DE HALLAZGO */}
      {selectedFinding && (
        <div className="drawer-backdrop" onClick={() => setSelectedFinding(null)}>
          <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div>
                <span className="page-eyebrow">HALLAZGO {selectedFinding.rule_id}</span>
                <h3 style={{ margin: '2px 0 0', color: 'var(--text-main)', fontSize: '17px' }}>
                  {selectedFinding.title}
                </h3>
              </div>
              <button className="header-icon-btn" onClick={() => setSelectedFinding(null)}>
                <X size={16} />
              </button>
            </div>

            <div className="drawer-body">
              <div className="card" style={{ background: 'var(--bg-elevated)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Severidad Normativa</span>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: selectedFinding.severity === 'Crítico' ? '#F43F5E' : '#F59E0B' }}>
                      {selectedFinding.severity} ({selectedFinding.risk_score} pts)
                    </div>
                  </div>
                  <span className="badge medium">{selectedFinding.status}</span>
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                  Fundamento Normativo (Rationale)
                </h4>
                <p style={{ fontSize: '13px', color: 'var(--text-main)', lineHeight: 1.5, background: 'var(--bg-input)', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>
                  {selectedFinding.rationale}
                </p>
              </div>

              <div>
                <h4 style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                  Evidencia Técnica Recolectada
                </h4>
                <pre style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', background: '#0a1424', padding: '10px', borderRadius: '4px', border: '1px solid var(--border-subtle)', whiteSpace: 'pre-wrap', color: '#7dd3fc' }}>
                  {selectedFinding.evidence}
                </pre>
              </div>

              {/* Botón de Explicabilidad IA */}
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <h4 style={{ fontSize: '13px', color: 'var(--color-primary)', margin: 0 }}>
                    Explicabilidad Heurística & IA
                  </h4>
                  <button className="btn btn-secondary btn-sm" onClick={handleExplain} disabled={explaining}>
                    <BrainCircuit size={14} /> {explaining ? 'Consultando...' : 'Explicar Hallazgo'}
                  </button>
                </div>
                {explanation && (
                  <p style={{ fontSize: '12px', color: 'var(--text-main)', lineHeight: 1.6, marginTop: '8px' }}>
                    {explanation}
                  </p>
                )}
              </div>

              {/* Acción de Remediación */}
              <div className="card">
                <h4 style={{ fontSize: '13px', color: 'var(--color-success)', marginBottom: '8px' }}>
                  Flujo de Remediación SOC
                </h4>
                <button className="btn btn-primary btn-sm" onClick={handleCreateRemediationTicket}>
                  <Ticket size={14} /> Generar Ticket de Remediación
                </button>
                {ticketSuccess && (
                  <p style={{ fontSize: '12px', color: '#10B981', marginTop: '8px' }}>{ticketSuccess}</p>
                )}
              </div>
            </div>

            <div className="drawer-footer">
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedFinding(null)}>
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
