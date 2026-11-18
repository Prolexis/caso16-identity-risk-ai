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
}) => {
  const currentInfo = navLabels[currentNav] ?? { group: 'SOC', label: currentNav }
  const isHealthy = health?.status === 'ok'

  return (
    <header className="header">
      <div className="header-left">
        <div className="breadcrumbs">
          <span>{currentInfo.group}</span>
          <span className="divider">/</span>
          <span className="current">{currentInfo.label}</span>
        </div>

        <div className="search-input-wrap" style={{ maxWidth: '320px', display: 'none' }}>
          <Search size={14} />
          <input
            type="text"
            className="search-input"
            placeholder="Buscar identidades, hallazgos..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>
      </div>

      <div className="header-right">
        {/* Estado del Backend */}
        <div className="backend-status-pill" title={`Conectado a ${health?.source || 'AD SharpHound'}`}>
          <span className={`pulse-dot ${isHealthy ? '' : 'error'}`} />
          <span>{isHealthy ? 'FastAPI Online' : 'Desconectado'}</span>
          <span style={{ opacity: 0.5 }}>·</span>
          <span>{health?.accounts_loaded ?? 113} identidades</span>
        </div>

        {/* Botón sincronizar */}
        <button
          className="header-icon-btn"
          onClick={onRefreshAll}
          title="Sincronizar telemetría con backend"
        >
          <RefreshCw size={16} className={loadingHealth ? 'spin' : ''} />
        </button>

        {/* Toggle Dark / Light */}
        <button
          className="header-icon-btn"
          onClick={onToggleTheme}
          title={theme === 'dark' ? 'Cambiar a Modo Claro' : 'Cambiar a Modo Oscuro'}
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {/* Selector de Rol RBAC */}
        <select
          className="role-selector"
          value={user.role}
          onChange={(e) => onChangeRole(e.target.value as UserRole)}
          title="Cambiar rol activo para pruebas de control de acceso"
        >
          <option value="Superadministrador">Superadministrador (Total)</option>
          <option value="Administrador de seguridad">Admin de Seguridad</option>
          <option value="Analista de ciberseguridad">Analista SOC</option>
          <option value="Responsable de remediación">Remediación</option>
          <option value="Auditor">Auditor de Cumplimiento</option>
          <option value="Usuario de consulta">Usuario de Consulta</option>
        </select>
      </div>
    </header>
  )
}
