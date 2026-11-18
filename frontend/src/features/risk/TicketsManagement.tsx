import React, { useState } from 'react'
import { Ticket, CheckCircle, Clock, Plus, Search } from 'lucide-react'
import { RemediationTicket } from '../../types'
import { updateTicket, createTicket } from '../../services/api'

interface TicketsManagementProps {
  tickets: RemediationTicket[]
  onRefresh: () => void
}

export const TicketsManagement: React.FC<TicketsManagementProps> = ({ tickets, onRefresh }) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [priorityFilter, setPriorityFilter] = useState('all')

  const [isCreating, setIsCreating] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newDesc, setNewDesc] = useState('')
  const [newPriority, setNewPriority] = useState('Media')
  const [newSla, setNewSla] = useState(7)
  const [savingTicket, setSavingTicket] = useState(false)

  const filteredTickets = tickets.filter((t) => {
    if (statusFilter !== 'all' && t.status !== statusFilter) return false
    if (priorityFilter !== 'all' && t.priority !== priorityFilter) return false
    if (searchTerm) {
      const q = searchTerm.toLowerCase()
      return t.title.toLowerCase().includes(q) || t.id.toLowerCase().includes(q) || (t.owner && t.owner.toLowerCase().includes(q))
    }
    return true
  })

  const handleCreate = async () => {
    if (!newTitle.trim()) return
    setSavingTicket(true)
    try {
      await createTicket({
        title: newTitle,
        description: newDesc || 'Remediación manual generada desde el Centro de Comando SOC.',
        priority: newPriority,
        sla_days: newSla,
      })
      setIsCreating(false)
      setNewTitle('')
      setNewDesc('')
      onRefresh()
    } catch (err) {
      console.error(err)
    } finally {
      setSavingTicket(false)
    }
  }

  const handleResolve = async (ticketId: string) => {
    try {
      await updateTicket(ticketId, { status: 'Resuelto', resolution_notes: 'Remediación confirmada por operador SOC.' })
      onRefresh()
    } catch (err) {
      console.error(err)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div className="page-eyebrow">SEGUIMIENTO DE SLA Y REMEDIACIÓN (M09)</div>
            <h2 className="page-title" style={{ fontSize: '24px' }}>Tickets de Remediación</h2>
            <p className="page-desc" style={{ margin: '4px 0 0' }}>
              Gestión del ciclo de vida de tratamiento de hallazgos críticos de identidad conforme a SLA.
            </p>
          </div>
          <button className="btn btn-primary btn-sm" onClick={() => setIsCreating(!isCreating)}>
            <Plus size={14} /> {isCreating ? 'Cancelar' : 'Nuevo Ticket'}
          </button>
        </div>

        {isCreating && (
          <div className="card" style={{ background: 'var(--bg-elevated)', marginBottom: '16px' }}>
            <h4 style={{ fontSize: '14px', marginBottom: '10px' }}>Crear Ticket de Remediación</h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <input
                type="text"
                className="search-input"
                placeholder="Título del ticket..."
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
              />
              <textarea
                className="search-input"
                placeholder="Descripción del plan de acción..."
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                style={{ minHeight: '60px' }}
              />
              <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <select className="select-filter" value={newPriority} onChange={(e) => setNewPriority(e.target.value)}>
                  <option value="Crítica">Prioridad Crítica (3 días SLA)</option>
                  <option value="Alta">Prioridad Alta (7 días SLA)</option>
                  <option value="Media">Prioridad Media (14 días SLA)</option>
                </select>
                <button className="btn btn-primary btn-sm" onClick={handleCreate} disabled={savingTicket}>
                  {savingTicket ? 'Creando...' : 'Guardar Ticket'}
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="filter-bar">
          <div className="search-input-wrap">
            <Search size={14} />
            <input
              type="text"
              className="search-input"
              placeholder="Buscar por ID, título o responsable..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <select className="select-filter" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="all">Todos los Estados</option>
            <option value="Abierto">Abierto</option>
            <option value="En progreso">En progreso</option>
            <option value="Resuelto">Resuelto</option>
          </select>
        </div>

        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID Ticket</th>
                <th>Título</th>
                <th>Prioridad</th>
                <th>Estado</th>
                <th>Responsable</th>
                <th>Vencimiento SLA</th>
                <th>Acción</th>
              </tr>
            </thead>
            <tbody>
              {filteredTickets.map((t) => (
                <tr key={t.id}>
                  <td><code>{t.id}</code></td>
                  <td><strong>{t.title}</strong></td>
                  <td>
                    <span className={`badge ${t.priority === 'Crítica' ? 'critical' : t.priority === 'Alta' ? 'high' : 'medium'}`}>
                      {t.priority}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${t.status === 'Resuelto' ? 'success' : 'low'}`}>
                      {t.status}
                    </span>
                  </td>
                  <td><span style={{ fontSize: '12px' }}>{t.owner || 'remediator@demo.local'}</span></td>
                  <td>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
                      {t.sla_due_date}
                    </span>
                  </td>
                  <td>
                    {t.status !== 'Resuelto' && (
                      <button className="btn btn-secondary btn-sm" onClick={() => handleResolve(t.id)}>
                        <CheckCircle size={12} /> Marcar Resuelto
                      </button>
                    )}
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
