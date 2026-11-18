import React, { useState } from 'react'
import {
  Bell,
  CheckCheck,
  X,
  ShieldAlert,
  Clock,
  KeyRound,
  Ticket,
  Cpu,
  ChevronRight,
  Filter,
} from 'lucide-react'
import { NavItemKey, SecurityNotification } from '../../types'

interface NotificationDrawerProps {
  isOpen: boolean
  onClose: () => void
  notifications: SecurityNotification[]
  onMarkAllAsRead: () => void
  onSelectNotification: (notif: SecurityNotification) => void
}

export const NotificationDrawer: React.FC<NotificationDrawerProps> = ({
  isOpen,
  onClose,
  notifications,
  onMarkAllAsRead,
  onSelectNotification,
}) => {
  const [filter, setFilter] = useState<'all' | 'critical' | 'threat' | 'ticket' | 'ai'>('all')

  if (!isOpen) return null

  const filteredNotifs = notifications.filter((n) => {
    if (filter === 'critical') return n.severity === 'critical'
    if (filter === 'threat') return n.category === 'threat' || n.category === 'orphan' || n.category === 'privilege'
    if (filter === 'ticket') return n.category === 'ticket'
    if (filter === 'ai') return n.category === 'ai'
    return true
  })

  const unreadCount = notifications.filter((n) => !n.read).length

  const getSeverityIcon = (n: SecurityNotification) => {
    switch (n.category) {
      case 'threat':
        return <ShieldAlert size={16} style={{ color: 'var(--destructive)' }} />
      case 'orphan':
        return <Clock size={16} style={{ color: 'var(--warning)' }} />
      case 'privilege':
        return <KeyRound size={16} style={{ color: '#C026D3' }} />
      case 'ticket':
        return <Ticket size={16} style={{ color: 'var(--primary)' }} />
      case 'ai':
        return <Cpu size={16} style={{ color: 'var(--secondary)' }} />
      default:
        return <Bell size={16} style={{ color: 'var(--primary)' }} />
    }
  }

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '480px' }}>
        {/* Header */}
        <div className="drawer-header" style={{ padding: '18px 22px' }}>
          <div>
            <div className="page-eyebrow">SOC ALERTS & TELEMETRY</div>
            <h3 style={{ margin: '2px 0 0', fontSize: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>Notificaciones de Seguridad</span>
              {unreadCount > 0 && (
                <span className="badge critical" style={{ fontSize: '10px' }}>
                  {unreadCount} nuevas
                </span>
              )}
            </h3>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {unreadCount > 0 && (
              <button
                className="btn btn-secondary btn-sm"
                onClick={onMarkAllAsRead}
                title="Marcar todas como leídas"
                style={{ fontSize: '11px', padding: '4px 8px' }}
              >
                <CheckCheck size={13} /> Leídas
              </button>
            )}
            <button className="header-icon-btn" onClick={onClose} aria-label="Cerrar panel">
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Filter Pills */}
        <div style={{ padding: '10px 22px', borderBottom: '1px solid var(--border)', display: 'flex', gap: '6px', overflowX: 'auto' }}>
          {[
            { id: 'all', label: 'Todas' },
            { id: 'critical', label: 'Críticas' },
            { id: 'threat', label: 'Identidades & Riesgo' },
            { id: 'ticket', label: 'SLA Tickets' },
            { id: 'ai', label: 'Modelos IA' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id as typeof filter)}
              className="btn btn-sm"
              style={{
                fontSize: '11px',
                padding: '4px 10px',
                background: filter === tab.id ? 'var(--primary)' : 'var(--surface-elevated)',
                color: filter === tab.id ? 'var(--primary-foreground)' : 'var(--muted-foreground)',
                borderColor: filter === tab.id ? 'var(--primary)' : 'var(--border)',
                whiteSpace: 'nowrap',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Notifications List */}
        <div className="drawer-body" style={{ padding: '16px 20px', gap: '10px' }}>
          {filteredNotifs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--muted-foreground)' }}>
              <Bell size={32} style={{ opacity: 0.3, marginBottom: '10px' }} />
              <p style={{ margin: 0, fontSize: '13px' }}>No hay notificaciones en este filtro.</p>
            </div>
          ) : (
            filteredNotifs.map((item) => (
              <div
                key={item.id}
                onClick={() => onSelectNotification(item)}
                style={{
                  padding: '14px 16px',
                  borderRadius: 'var(--radius-md)',
                  background: item.read ? 'var(--surface)' : 'var(--surface-elevated)',
                  border: '1px solid',
                  borderColor: item.read ? 'var(--border)' : 'var(--border-highlight)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  gap: '12px',
                  alignItems: 'flex-start',
                  boxShadow: item.read ? 'none' : 'var(--shadow-sm)',
                }}
              >
                <div style={{ marginTop: '2px' }}>{getSeverityIcon(item)}</div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3px' }}>
                    <strong style={{ fontSize: '12.5px', color: 'var(--foreground)' }}>
                      {item.title}
                    </strong>
                    {!item.read && (
                      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--primary)' }} />
                    )}
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--muted-foreground)', margin: '0 0 6px', lineHeight: 1.4 }}>
                    {item.description}
                  </p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
                    <span style={{ color: 'var(--muted-foreground)', opacity: 0.8 }}>{item.timestamp}</span>
                    <span style={{ color: 'var(--primary)', display: 'flex', alignItems: 'center', gap: '2px', fontWeight: 500 }}>
                      Inspeccionar <ChevronRight size={12} />
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="drawer-footer" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '11px', color: 'var(--muted-foreground)' }}>
            Telemetría de eventos SharpHound AD & Optuna
          </span>
          <button className="btn btn-secondary btn-sm" onClick={onClose}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  )
}
