import React from 'react'
import {
  Sun,
  Moon,
  Search,
  RefreshCw,
  Bell,
  CheckCircle2,
  AlertCircle,
  Database,
  ShieldCheck,
  User,
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
  findingsCount?: number
}

const navLabels: Record<NavItemKey, { group: string; label: string }> = {
  dashboard: { group: 'Centro de Operaciones', label: 'Security Overview' },
  'security-monitor': { group: 'Centro de Operaciones', label: 'Monitoreo en Vivo' },
  identities: { group: 'Gestión de Identidades', label: 'Inventario de Cuentas' },
  orphans: { group: 'Gestión de Identidades', label: 'Cuentas Huérfanas (R01)' },
  'excessive-privs': { group: 'Gestión de Identidades', label: 'Privilegios Excesivos' },
  directories: { group: 'Gestión de Identidades', label: 'Directorios AD/LDAP' },
  'ai-training-center': { group: 'Inteligencia Artificial', label: 'AI Training Center' },
  'ai-eda': { group: 'Inteligencia Artificial', label: 'Exploración de Datos (EDA)' },
  'ai-models-config': { group: 'Inteligencia Artificial', label: 'Configuración M1/M2/M3' },
  'ai-execution': { group: 'Inteligencia Artificial', label: 'Consola & Optuna' },
  'ai-evaluation': { group: 'Inteligencia Artificial', label: 'Métricas & Validación' },
  'ai-comparison': { group: 'Inteligencia Artificial', label: 'Comparación de Modelos' },
  'ai-explainability': { group: 'Inteligencia Artificial', label: 'Explicabilidad IA' },
  findings: { group: 'Gestión de Riesgos', label: 'Hallazgos de Seguridad' },
  tickets: { group: 'Gestión de Riesgos', label: 'Tickets de Remediación' },
  rules: { group: 'Gestión de Riesgos', label: 'Reglas de Detección' },
  automation: { group: 'Automatización', label: 'Workflows n8n & LangFlow' },
  reports: { group: 'Reportes y Auditoría', label: 'Centro de Reportes' },
  audit: { group: 'Reportes y Auditoría', label: 'Bitácora de Auditoría' },
  policies: { group: 'Administración', label: 'Políticas de Seguridad' },
  'users-roles': { group: 'Administración', label: 'Usuarios y Roles' },
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
  searchQuery,
  onSearchChange,
  findingsCount = 269,
}) => {
  const currentInfo = navLabels[currentNav] ?? { group: 'SOC', label: currentNav }
  const isHealthy = health?.status === 'ok'
  const [currentTime, setCurrentTime] = React.useState<string>(() => {
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
          <span>{isHealthy ? 'FastAPI Conectado' : 'Desconectado'}</span>
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
          <RefreshCw size={15} className={loadingHealth ? 'spin-anim' : ''} />
        </button>

        {/* Centro de notificaciones */}
        <button
          className="header-icon-btn has-notifications"
          title={`${findingsCount} hallazgos activos en el SOC`}
          aria-label="Notificaciones"
        >
          <Bell size={15} />
          {findingsCount > 0 && (
            <span className="header-notification-badge">
              {findingsCount > 99 ? '99+' : findingsCount}
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

        {/* Selector de Rol RBAC y Usuario */}
        <div className="role-selector-wrap" title="Cambiar rol activo para pruebas RBAC">
          <User size={13} style={{ color: 'var(--muted-foreground)' }} />
          <select
            className="role-selector"
            value={user.role}
            onChange={(e) => onChangeRole(e.target.value as UserRole)}
            aria-label="Selector de rol RBAC"
          >
            <option value="Admin">Admin (Control Total)</option>
            <option value="SOC_Analyst">Analista SOC</option>
            <option value="Auditor">Auditor (Solo Lectura)</option>
            <option value="Security_Engineer">Ingeniero Seg.</option>
          </select>
        </div>
      </div>
    </header>
  )
}
