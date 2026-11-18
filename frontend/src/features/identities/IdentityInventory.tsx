import React, { useState, useMemo } from 'react'
import {
  Search,
  Filter,
  Users,
  Shield,
  Clock,
  KeyRound,
  CheckCircle,
  XCircle,
  AlertTriangle,
  X,
  Lock,
} from 'lucide-react'
import { DirectoryAccount } from '../../types'
import { updateAccountMetadata } from '../../services/api'

interface IdentityInventoryProps {
  accounts: DirectoryAccount[]
  filterType?: 'all' | 'orphans' | 'excessive'
  onRefresh: () => void
}

export const IdentityInventory: React.FC<IdentityInventoryProps> = ({
  accounts,
  filterType = 'all',
  onRefresh,
}) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [domainFilter, setDomainFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [riskFilter, setRiskFilter] = useState('all')
  const [selectedAccount, setSelectedAccount] = useState<DirectoryAccount | null>(null)
  const [isUpdating, setIsUpdating] = useState(false)
  const [justificationText, setJustificationText] = useState('')
  const [justificationVerified, setJustificationVerified] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string | null>(null)

  const filteredAccounts = useMemo(() => {
    return accounts.filter((acc) => {
      // Filtro especial por tipo de pantalla
      if (filterType === 'orphans') {
        const isInactive = !acc.last_activity || (new Date().getTime() - new Date(acc.last_activity).getTime()) / (1000 * 3600 * 24) >= 90
        if (!isInactive) return false
      }
      if (filterType === 'excessive') {
        if (!acc.is_admin && acc.risk_score < 60) return false
      }

      // Búsqueda de texto
      if (searchTerm) {
        const q = searchTerm.toLowerCase()
        const match =
          acc.username.toLowerCase().includes(q) ||
          acc.display_name.toLowerCase().includes(q) ||
          acc.external_id.toLowerCase().includes(q) ||
          (acc.email && acc.email.toLowerCase().includes(q)) ||
          acc.privileged_roles.toLowerCase().includes(q)
        if (!match) return false
      }

      // Filtro de Dominio
      if (domainFilter !== 'all') {
        if (!acc.source.toLowerCase().includes(domainFilter.toLowerCase())) return false
      }

      // Filtro de Tipo
      if (typeFilter !== 'all') {
        if (acc.account_type.toLowerCase() !== typeFilter.toLowerCase()) return false
      }

      // Filtro de Riesgo
      if (riskFilter !== 'all') {
        if (riskFilter === 'critical' && acc.risk_score < 80) return false
        if (riskFilter === 'high' && (acc.risk_score < 60 || acc.risk_score >= 80)) return false
        if (riskFilter === 'medium' && (acc.risk_score < 35 || acc.risk_score >= 60)) return false
        if (riskFilter === 'low' && acc.risk_score >= 35) return false
      }

      return true
    })
  }, [accounts, filterType, searchTerm, domainFilter, typeFilter, riskFilter])

  const handleOpenDetail = (acc: DirectoryAccount) => {
    setSelectedAccount(acc)
    setJustificationVerified(acc.justification_verified)
    setJustificationText('')
    setSaveMessage(null)
  }

  const handleSaveMetadata = async () => {
    if (!selectedAccount) return
    setIsUpdating(true)
    setSaveMessage(null)
    try {
      await updateAccountMetadata(selectedAccount.id, {
        justification_verified: justificationVerified,
        privilege_justification: justificationText || 'Aprobado formalmente por auditoría de seguridad',
      })
      setSaveMessage('Metadatos actualizados en la base de datos.')
      onRefresh()
    } catch (err: unknown) {
      setSaveMessage(`Error: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setIsUpdating(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div className="page-eyebrow">ACTIVE DIRECTORY / LDAP TELEMETRY</div>
            <h2 className="page-title" style={{ fontSize: '24px' }}>
              {filterType === 'orphans'
                ? 'Cuentas Inactivas y Huérfanas (Regla R01)'
                : filterType === 'excessive'
                ? 'Identidades con Privilegios Excesivos o Desalineados'
                : 'Inventario Unificado de Identidades'}
            </h2>
            <p className="page-desc" style={{ margin: '4px 0 0' }}>
              Total: {filteredAccounts.length} de {accounts.length} cuentas registradas en los 4 dominios corporativos.
            </p>
          </div>
        </div>

        {/* Barra de Filtros */}
        <div className="filter-bar">
          <div className="search-input-wrap">
            <Search size={14} />
            <input
              type="text"
              className="search-input"
              placeholder="Buscar por usuario, correo, ID o grupo AD..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <select
            className="select-filter"
            value={domainFilter}
            onChange={(e) => setDomainFilter(e.target.value)}
          >
            <option value="all">Todos los Dominios AD</option>
            <option value="PHANTOM">PHANTOM.CORP</option>
            <option value="WRAITH">WRAITH.CORP</option>
            <option value="ESC1">ESC1.LOCAL</option>
            <option value="GHOST">GHOST.CORP</option>
          </select>

          <select
            className="select-filter"
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option value="all">Todos los Tipos</option>
            <option value="user">Usuario Humano</option>
            <option value="service">Cuenta de Servicio</option>
          </select>

          <select
            className="select-filter"
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
          >
            <option value="all">Cualquier Nivel de Riesgo</option>
            <option value="critical">Crítico (Score ≥ 80)</option>
            <option value="high">Alto (Score 60–79)</option>
            <option value="medium">Medio (Score 35–59)</option>
            <option value="low">Bajo (Score &lt; 35)</option>
          </select>

          {(searchTerm || domainFilter !== 'all' || typeFilter !== 'all' || riskFilter !== 'all') && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setSearchTerm('')
                setDomainFilter('all')
                setTypeFilter('all')
                setRiskFilter('all')
              }}
            >
              Limpiar Filtros
            </button>
          )}
        </div>

        {/* Tabla de Identidades */}
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Cuenta / Identidad</th>
                <th>Dominio AD</th>
                <th>Tipo</th>
                <th>Estado</th>
                <th>Privilegios Administrativos</th>
                <th>Última Actividad</th>
                <th>Score</th>
                <th>Severidad</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {filteredAccounts.length === 0 ? (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-dim)' }}>
                    No se encontraron identidades que coincidan con los criterios de búsqueda.
                  </td>
                </tr>
              ) : (
                filteredAccounts.map((acc) => (
                  <tr key={acc.id}>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <strong style={{ color: 'var(--text-main)', fontSize: '13px' }}>{acc.username}</strong>
                        <span style={{ fontSize: '11px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                          {acc.display_name} · {acc.external_id}
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
                      <span className={`badge ${acc.active ? 'success' : 'critical'}`}>
                        {acc.active ? 'Activa' : 'Deshabilitada'}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <span style={{ fontSize: '11px', color: acc.is_admin ? '#F43F5E' : 'var(--text-muted)', fontWeight: acc.is_admin ? 600 : 400 }}>
                          {acc.is_admin ? '🛡️ Domain Admin' : 'Estándar'}
                        </span>
                        {acc.privileged_roles && (
                          <span style={{ fontSize: '10px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                            {acc.privileged_roles.split('|').slice(0, 2).join(', ')}
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                        {acc.last_activity ? acc.last_activity : <span style={{ color: '#F59E0B' }}>Sin logon</span>}
                      </span>
                    </td>
                    <td>
                      <strong style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '13px',
                        color: acc.risk_score >= 80 ? '#F43F5E' : acc.risk_score >= 60 ? '#F59E0B' : '#818CF8'
                      }}>
                        {acc.risk_score}
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
                        onClick={() => handleOpenDetail(acc)}
                      >
                        Detalles
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* DRAWER LATERAL DE DETALLE DE CUENTA */}
      {selectedAccount && (
        <div className="drawer-backdrop" onClick={() => setSelectedAccount(null)}>
          <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div>
                <span className="page-eyebrow">FICHA TÉCNICA DE IDENTIDAD</span>
                <h3 style={{ margin: '2px 0 0', color: 'var(--text-main)', fontSize: '18px' }}>
                  {selectedAccount.username}
                </h3>
              </div>
              <button
                className="header-icon-btn"
                onClick={() => setSelectedAccount(null)}
              >
                <X size={16} />
              </button>
            </div>

            <div className="drawer-body">
              {/* Resumen de Riesgo */}
              <div className="card" style={{ background: 'var(--bg-elevated)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Puntaje Determinista</span>
                    <div style={{
                      fontFamily: 'var(--font-display)',
                      fontSize: '32px',
                      fontWeight: 700,
                      color: selectedAccount.risk_score >= 80 ? '#F43F5E' : selectedAccount.risk_score >= 60 ? '#F59E0B' : '#818CF8'
                    }}>
                      {selectedAccount.risk_score} / 100
                    </div>
                  </div>
                  <span className={`badge ${selectedAccount.risk_score >= 80 ? 'critical' : selectedAccount.risk_score >= 60 ? 'high' : 'medium'}`}>
                    Riesgo {selectedAccount.risk_score >= 80 ? 'Crítico' : selectedAccount.risk_score >= 60 ? 'Alto' : 'Medio'}
                  </span>
                </div>
              </div>

              {/* Atributos Clave */}
              <div>
                <h4 style={{ color: 'var(--text-muted)', fontSize: '12px', textTransform: 'uppercase', marginBottom: '8px' }}>
                  Atributos de Active Directory
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
                    <span style={{ color: 'var(--text-dim)' }}>External ID:</span>
                    <code>{selectedAccount.external_id}</code>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
                    <span style={{ color: 'var(--text-dim)' }}>Dominio / Fuente:</span>
                    <span>{selectedAccount.source}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
                    <span style={{ color: 'var(--text-dim)' }}>Tipo de Cuenta:</span>
                    <span className="badge medium">{selectedAccount.account_type}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
                    <span style={{ color: 'var(--text-dim)' }}>Último Logon:</span>
                    <span>{selectedAccount.last_activity || 'Sin registro en AD'}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
                    <span style={{ color: 'var(--text-dim)' }}>Clave Nunca Expira (R04):</span>
                    <span style={{ color: selectedAccount.password_never_expires ? '#F43F5E' : 'var(--text-main)' }}>
                      {selectedAccount.password_never_expires ? '⚠️ Sí (Eterna)' : 'No'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '4px' }}>
                    <span style={{ color: 'var(--text-dim)' }}>Cuenta Duplicada (R03):</span>
                    <span>{selectedAccount.is_duplicate ? '⚠️ Sí' : 'No'}</span>
                  </div>
                </div>
              </div>

              {/* Roles y Privilegios */}
              <div>
                <h4 style={{ color: 'var(--text-muted)', fontSize: '12px', textTransform: 'uppercase', marginBottom: '8px' }}>
                  Membresía de Grupos LDAP
                </h4>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {selectedAccount.privileged_roles.split('|').filter(Boolean).map((role, idx) => (
                    <span key={idx} className="badge" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-subtle)' }}>
                      {role}
                    </span>
                  ))}
                </div>
              </div>

              {/* Justificación y Gobierno */}
              <div className="card">
                <h4 style={{ color: 'var(--color-primary)', fontSize: '13px', marginBottom: '10px' }}>
                  Gobierno de Privilegios (Regla R02)
                </h4>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', marginBottom: '12px' }}>
                  <input
                    type="checkbox"
                    checked={justificationVerified}
                    onChange={(e) => setJustificationVerified(e.target.checked)}
                  />
                  <span>Privilegio Administrativo Justificado y Verificado</span>
                </label>

                <textarea
                  className="search-input"
                  style={{ minHeight: '70px', padding: '8px 10px', fontSize: '12px' }}
                  placeholder="Motivo o ticket de justificación de privilegios..."
                  value={justificationText}
                  onChange={(e) => setJustificationText(e.target.value)}
                />

                <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleSaveMetadata}
                    disabled={isUpdating}
                  >
                    {isUpdating ? 'Guardando...' : 'Actualizar Justificación'}
                  </button>
                  {saveMessage && <span style={{ fontSize: '11px', color: '#10B981' }}>{saveMessage}</span>}
                </div>
              </div>
            </div>

            <div className="drawer-footer">
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedAccount(null)}>
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
