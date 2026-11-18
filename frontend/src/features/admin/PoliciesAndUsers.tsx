import React, { useState } from 'react'
import { Settings, UserCheck, Shield, Edit2, Check, X } from 'lucide-react'
import { SecurityPolicy, SystemRole, SystemUser } from '../../types'
import { updatePolicy } from '../../services/api'

interface PoliciesAndUsersProps {
  policies: SecurityPolicy[]
  users: SystemUser[]
  roles: SystemRole[]
  onRefresh: () => void
}

export const PoliciesAndUsers: React.FC<PoliciesAndUsersProps> = ({
  policies,
  users,
  roles,
  onRefresh,
}) => {
  const [editingPolicyId, setEditingPolicyId] = useState<number | null>(null)
  const [editValue, setEditValue] = useState<number>(0)
  const [editActive, setEditActive] = useState<boolean>(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const handleStartEdit = (p: SecurityPolicy) => {
    setEditingPolicyId(p.id)
    setEditValue(p.threshold_value)
    setEditActive(p.is_active)
    setMsg(null)
  }

  const handleSave = async (policyId: number) => {
    setSaving(true)
    try {
      await updatePolicy(policyId, {
        threshold_value: editValue,
        is_active: editActive,
      })
      setMsg('Política actualizada correctamente.')
      setEditingPolicyId(null)
      onRefresh()
    } catch (err: unknown) {
      setMsg(`Error: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* POLÍTICAS DE SEGURIDAD */}
      <div className="card">
        <div className="page-eyebrow">POLÍTICAS Y UMBRALES NORMATIVOS (M14)</div>
        <h2 className="page-title" style={{ fontSize: '24px' }}>Políticas de Gobierno de Identidades</h2>
        <p className="page-desc" style={{ margin: '4px 0 16px' }}>
          Definen los umbrales deterministas de días de inactividad, scores de riesgo y exigencias de justificación aplicados por las reglas R01–R06.
        </p>

        {msg && <p style={{ color: '#10B981', fontSize: '13px', marginBottom: '10px' }}>{msg}</p>}

        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Código</th>
                <th>Nombre de la Política</th>
                <th>Descripción</th>
                <th>Umbral / Valor</th>
                <th>Unidad</th>
                <th>Estado</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {policies.map((p) => {
                const isEditing = editingPolicyId === p.id
                return (
                  <tr key={p.id}>
                    <td><code>{p.code}</code></td>
                    <td><strong>{p.name}</strong></td>
                    <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{p.description}</td>
                    <td>
                      {isEditing ? (
                        <input
                          type="number"
                          className="search-input"
                          style={{ width: '80px', padding: '4px 8px' }}
                          value={editValue}
                          onChange={(e) => setEditValue(parseInt(e.target.value) || 0)}
                        />
                      ) : (
                        <strong style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', color: 'var(--color-primary)' }}>
                          {p.threshold_value}
                        </strong>
                      )}
                    </td>
                    <td><span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{p.unit}</span></td>
                    <td>
                      <span className={`badge ${p.is_active ? 'success' : 'critical'}`}>
                        {p.is_active ? 'Activa' : 'Inactiva'}
                      </span>
                    </td>
                    <td>
                      {isEditing ? (
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <button className="btn btn-primary btn-sm" onClick={() => handleSave(p.id)} disabled={saving}>
                            <Check size={12} />
                          </button>
                          <button className="btn btn-secondary btn-sm" onClick={() => setEditingPolicyId(null)}>
                            <X size={12} />
                          </button>
                        </div>
                      ) : (
                        <button className="btn btn-secondary btn-sm" onClick={() => handleStartEdit(p)}>
                          <Edit2 size={12} /> Editar
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* USUARIOS Y ROLES RBAC */}
      <div className="grid-cols-2">
        <div className="card">
          <span className="card-title">Usuarios del Sistema (IAM)</span>
          <table className="data-table" style={{ marginTop: '12px' }}>
            <thead>
              <tr>
                <th>Usuario</th>
                <th>Nombre</th>
                <th>Rol</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td><code>{u.username}</code></td>
                  <td>{u.full_name}</td>
                  <td><span className="badge medium">{u.role}</span></td>
                  <td><span className="badge success">{u.active ? 'Activo' : 'Inactivo'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <span className="card-title">Roles y Permisos Granulares</span>
          <table className="data-table" style={{ marginTop: '12px' }}>
            <thead>
              <tr>
                <th>Rol</th>
                <th>Permisos</th>
              </tr>
            </thead>
            <tbody>
              {roles.map((r) => (
                <tr key={r.id}>
                  <td><strong>{r.name}</strong></td>
                  <td>
                    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                      {r.permissions.split(',').map((perm) => (
                        <span key={perm} className="badge low" style={{ fontSize: '9px' }}>
                          {perm.trim()}
                        </span>
                      ))}
                    </div>
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
