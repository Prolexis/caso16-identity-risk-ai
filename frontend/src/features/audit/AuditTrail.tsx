import React, { useState, useMemo } from 'react'
import { Clock, Search, ShieldCheck, User } from 'lucide-react'
import { AuditLogItem } from '../../types'

interface AuditTrailProps {
  logs: AuditLogItem[]
}

export const AuditTrail: React.FC<AuditTrailProps> = ({ logs }) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [actionFilter, setActionFilter] = useState('all')

  const filteredLogs = useMemo(() => {
    return logs.filter((l) => {
      if (actionFilter !== 'all' && !l.action.toLowerCase().includes(actionFilter.toLowerCase())) return false
      if (searchTerm) {
        const q = searchTerm.toLowerCase()
        return (
          l.actor.toLowerCase().includes(q) ||
          l.action.toLowerCase().includes(q) ||
          l.resource.toLowerCase().includes(q) ||
          l.details.toLowerCase().includes(q)
        )
      }
      return true
    })
  }, [logs, actionFilter, searchTerm])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="card">
        <div className="page-eyebrow">REGISTRO INMUTABLE Y TRAZABILIDAD (M03)</div>
        <h2 className="page-title" style={{ fontSize: '24px' }}>Bitácora de Auditoría Integral</h2>
        <p className="page-desc" style={{ margin: '4px 0 0' }}>
          Registro append-only de todas las operaciones de autenticación, escaneos, modificaciones de metadatos y entrenamientos de IA.
        </p>

        <div className="filter-bar" style={{ marginTop: '16px' }}>
          <div className="search-input-wrap">
            <Search size={14} />
            <input
              type="text"
              className="search-input"
              placeholder="Buscar por actor, acción, recurso o IP..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <select
            className="select-filter"
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
          >
            <option value="all">Todas las Acciones</option>
            <option value="login">Autenticación (login)</option>
            <option value="scan">Escaneo de Identidades</option>
            <option value="train">Entrenamiento IA</option>
            <option value="update">Modificaciones</option>
          </select>
        </div>

        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Fecha y Hora (UTC)</th>
                <th>Actor</th>
                <th>Rol</th>
                <th>Acción</th>
                <th>Recurso</th>
                <th>Resultado</th>
                <th>IP Origen</th>
                <th>Detalles</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log) => (
                <tr key={log.id}>
                  <td>
                    <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                      {new Date(log.occurred_at).toLocaleString('es-PE')}
                    </span>
                  </td>
                  <td>
                    <strong style={{ color: 'var(--text-main)', fontSize: '12px' }}>{log.actor}</strong>
                  </td>
                  <td>
                    <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{log.role}</span>
                  </td>
                  <td>
                    <code style={{ fontSize: '11px', color: 'var(--color-primary)' }}>{log.action}</code>
                  </td>
                  <td>
                    <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}>{log.resource}</span>
                  </td>
                  <td>
                    <span className={`badge ${log.result === 'success' ? 'success' : 'critical'}`}>
                      {log.result}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}>{log.ip_address}</span>
                  </td>
                  <td>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{log.details}</span>
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
