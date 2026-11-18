import React, { useState } from 'react'
import {
  Sun,
  Moon,
  RefreshCw,
  Bell,
  User,
  LogIn,
  ChevronDown,
} from 'lucide-react'
import { HealthResponse, NavItemKey, ThemeMode, UserProfile, UserRole } from '../../types'

interface HeaderProps {
  currentNav: NavItemKey
  theme: ThemeMode
  onToggleTheme: () => void
  user: UserProfile
  onChangeRole: (newRole: UserRole) => void
  health?: HealthResponse | null
  loadingHealth: boolean
  onRefreshAll: () => void
  searchQuery: string
  onSearchChange: (q: string) => void
  unreadNotificationsCount?: number
  onOpenNotifications: () => void
  onOpenLoginModal: () => void
}

const navLabels: Record<string, { group: string; label: string }> = {
  dashboard: { group: 'Operaciones SOC', label: 'Security Overview' },
  'security-monitor': { group: 'Operaciones SOC', label: 'Monitoreo en Vivo' },
  identities: { group: 'Identidades (ITDR)', label: 'Inventario de Cuentas' },
  orphans: { group: 'Identidades (ITDR)', label: 'Cuentas Huérfanas (R01)' },
  'excessive-privs': { group: 'Identidades (ITDR)', label: 'Privilegios Excesivos' },
  directories: { group: 'Identidades (ITDR)', label: 'Directorios AD / LDAP' },
  'ai-training-center': { group: 'Inteligencia Artificial', label: 'AI Training Center (MLOps)' },
  findings: { group: 'Gestión de Amenazas', label: 'Hallazgos de Seguridad' },
  tickets: { group: 'Gestión de Amenazas', label: 'Tickets de Remediación' },
  rules: { group: 'Gestión de Amenazas', label: 'Reglas de Detección (R01–R06)' },
  automation: { group: 'Automatización & SOAR', label: 'Workflows n8n & LangFlow' },
  reports: { group: 'Gobierno & Auditoría', label: 'Centro de Reportes' },
  audit: { group: 'Gobierno & Auditoría', label: 'Bitácora de Auditoría' },
  policies: { group: 'Gobierno & Auditoría', label: 'Políticas & Roles RBAC' },
}

export const Header: React.FC<HeaderProps> = ({
  currentNav,
  theme,
  onToggleTheme,
  user,
  onChangeRole,
  health,
  loadingHealth,
  onRefreshAll,
  unreadNotificationsCount = 5,
  onOpenNotifications,
  onOpenLoginModal,
}) => {
  const currentInfo = navLabels[currentNav] ?? { group: 'Command Center', label: currentNav }
  const isHealthy = health?.status === 'ok'
  const [currentTime, setCurrentTime] = useState<string>(() => {
    const d = new Date()
    return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  })

  const handleManualRefresh = () => {
    const d = new Date()
    setCurrentTime(`${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`)
    onRefreshAll()
  }

  return (
    <header className="header">
      <div className="header-left">
        <div className="breadcrumbs">
          <span>{currentInfo.group}</span>
          <span className="divider">/</span>
          <span className="current">{currentInfo.label}</span>
        </div>
      </div>

      <div className="header-right">
        {/* Estado del Backend FastAPI */}
        <div className="backend-status-pill" title={`Conectado a ${health?.source || 'AD SharpHound'}`}>
          <span className={`pulse-dot ${isHealthy ? '' : 'error'}`} />
          <span>{isHealthy ? 'FastAPI Online' : 'Desconectado'}</span>
          <span style={{ opacity: 0.4 }}>·</span>
          <span>{health?.accounts_loaded ?? 113} cuentas</span>
        </div>

        {/* Última actualización */}
        <div style={{ fontSize: '11px', color: 'var(--muted-foreground)' }} title="Hora del último sondeo">
          Actualizado: <strong style={{ color: 'var(--foreground)' }}>{currentTime}</strong>
        </div>

        {/* Botón sincronizar */}
        <button
          className="header-icon-btn"
          onClick={handleManualRefresh}
          title="Sincronizar telemetría con FastAPI"
          aria-label="Sincronizar datos"
        >
          <RefreshCw size={14} className={loadingHealth ? 'spin-anim' : ''} />
        </button>

        {/* Centro de notificaciones INTERACTIVO */}
        <button
          className="header-icon-btn has-notifications"
          onClick={onOpenNotifications}
          title={`${unreadNotificationsCount} notificaciones de seguridad sin leer`}
          aria-label="Abrir centro de notificaciones"
        >
          <Bell size={15} />
          {unreadNotificationsCount > 0 && (
            <span className="header-notification-badge">
              {unreadNotificationsCount > 99 ? '99+' : unreadNotificationsCount}
            </span>
          )}
        </button>

        {/* Selector de Tema Claro / Oscuro */}
        <button
          className="header-icon-btn"
          onClick={onToggleTheme}
          title={theme === 'dark' ? 'Cambiar a Modo Claro' : 'Cambiar a Modo Oscuro'}
          aria-label="Alternar tema claro y oscuro"
        >
          {theme === 'dark' ? <Sun size={15} style={{ color: 'var(--warning)' }} /> : <Moon size={15} style={{ color: 'var(--primary)' }} />}
        </button>

        {/* Selector de Rol RBAC INTERACTIVO */}
        <div className="role-selector-wrap" title="Cambiar rol activo para pruebas RBAC">
          <User size={13} style={{ color: 'var(--primary)' }} />
          <select
            className="role-selector"
            value={user.role}
            onChange={(e) => onChangeRole(e.target.value as UserRole)}
            aria-label="Selector de rol RBAC"
          >
            <option value="Superadministrador">🛡️ Superadministrador</option>
            <option value="Analista de ciberseguridad">🔍 Analista SOC L2</option>
            <option value="Auditor">📋 Auditor (ISO 27001)</option>
            <option value="Administrador de seguridad">⚙️ Ingeniero Seg. (AI)</option>
          </select>
        </div>

        {/* Botón de Login / Perfil */}
        <button
          className="btn btn-secondary btn-sm"
          onClick={onOpenLoginModal}
          title="Abrir modal de inicio de sesión con autocompletado"
          style={{ gap: '6px', fontSize: '11.5px', padding: '5px 10px' }}
        >
          <LogIn size={13} />
          <span>Login Demo</span>
        </button>
      </div>
    </header>
  )
}
