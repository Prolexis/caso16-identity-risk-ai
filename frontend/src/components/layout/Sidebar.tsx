import React from 'react'
import {
  Shield,
  Activity,
  Users,
  UserX,
  KeyRound,
  Database,
  Cpu,
  LineChart,
  Sliders,
  PlayCircle,
  FileCheck,
  Scale,
  BrainCircuit,
  AlertTriangle,
  Ticket,
  FileCode,
  Workflow,
  FileSpreadsheet,
  Clock,
  Settings,
  UserCheck,
  ChevronLeft,
  ChevronRight,
  LogOut,
} from 'lucide-react'
import { NavItemKey, UserProfile } from '../../types'

interface SidebarProps {
  currentNav: NavItemKey
  onSelectNav: (key: NavItemKey) => void
  collapsed: boolean
  onToggleCollapse: () => void
  user: UserProfile
  counts?: {
    findings?: number
    orphans?: number
    excessive?: number
  }
}

interface NavGroup {
  label: string
  items: Array<{
    key: NavItemKey
    label: string
    icon: React.ElementType
    badge?: number | string
  }>
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentNav,
  onSelectNav,
  collapsed,
  onToggleCollapse,
  user,
  counts,
}) => {
  const groups: NavGroup[] = [
    {
      label: 'Centro de Operaciones',
      items: [
        { key: 'dashboard', label: 'Security Overview', icon: Shield },
        { key: 'security-monitor', label: 'Monitoreo en Vivo', icon: Activity },
      ],
    },
    {
      label: 'Gestión de Identidades',
      items: [
        { key: 'identities', label: 'Inventario de Cuentas', icon: Users },
        { key: 'orphans', label: 'Cuentas Huérfanas (R01)', icon: UserX, badge: counts?.orphans ?? 81 },
        { key: 'excessive-privs', label: 'Privilegios Excesivos', icon: KeyRound, badge: counts?.excessive ?? 64 },
        { key: 'directories', label: 'Directorios AD/LDAP', icon: Database },
      ],
    },
    {
      label: 'Inteligencia Artificial',
      items: [
        { key: 'ai-training-center', label: 'AI Training Center', icon: Cpu, badge: 'M1·M2·M3' },
        { key: 'ai-eda', label: 'Exploración de Datos (EDA)', icon: LineChart },
        { key: 'ai-models-config', label: 'Configuración M1/M2/M3', icon: Sliders },
        { key: 'ai-execution', label: 'Consola & Optuna', icon: PlayCircle },
        { key: 'ai-evaluation', label: 'Métricas & Validación', icon: FileCheck },
        { key: 'ai-comparison', label: 'Comparación de Modelos', icon: Scale },
        { key: 'ai-explainability', label: 'Explicabilidad IA', icon: BrainCircuit },
      ],
    },
    {
      label: 'Gestión de Riesgos',
      items: [
        { key: 'findings', label: 'Hallazgos de Seguridad', icon: AlertTriangle, badge: counts?.findings ?? 269 },
        { key: 'tickets', label: 'Tickets de Remediación', icon: Ticket },
        { key: 'rules', label: 'Reglas de Detección (R01–R06)', icon: FileCode },
      ],
    },
    {
      label: 'Automatización',
      items: [
        { key: 'automation', label: 'Workflows n8n & LangFlow', icon: Workflow },
      ],
    },
    {
      label: 'Reportes y Auditoría',
      items: [
        { key: 'reports', label: 'Centro de Reportes', icon: FileSpreadsheet },
        { key: 'audit', label: 'Bitácora de Auditoría', icon: Clock },
      ],
    },
    {
      label: 'Administración',
      items: [
        { key: 'policies', label: 'Políticas de Seguridad', icon: Settings },
        { key: 'users-roles', label: 'Usuarios y Roles RBAC', icon: UserCheck },
      ],
    },
  ]

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="brand-badge">C16</div>
          {!collapsed && (
            <div className="brand-info">
              <span className="brand-title">CASO16</span>
              <span className="brand-subtitle">Threat Intelligence</span>
            </div>
          )}
        </div>
        <button
          className="sidebar-toggle-btn"
          onClick={onToggleCollapse}
          title={collapsed ? 'Expandir barra lateral' : 'Colapsar barra lateral'}
          aria-label="Alternar barra lateral"
        >
          {collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
        </button>
      </div>

      <nav className="sidebar-nav">
        {groups.map((group) => (
          <div key={group.label} className="nav-group">
            {!collapsed && <div className="nav-group-label">{group.label}</div>}
            <ul className="nav-items-list">
              {group.items.map((item) => {
                const Icon = item.icon
                const isActive = currentNav === item.key
                return (
                  <li key={item.key}>
                    <button
                      className={`nav-link ${isActive ? 'active' : ''}`}
                      onClick={() => onSelectNav(item.key)}
                      title={collapsed ? item.label : undefined}
                    >
                      <Icon className="nav-icon" />
                      {!collapsed && <span>{item.label}</span>}
                      {!collapsed && item.badge !== undefined && (
                        <span className="nav-badge">{item.badge}</span>
                      )}
                    </button>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="user-mini-card">
          <div className="user-avatar">
            {user.fullName.slice(0, 2).toUpperCase()}
          </div>
          {!collapsed && (
            <div className="user-details" style={{ flex: 1 }}>
              <span className="user-name">{user.fullName}</span>
              <span className="user-role">{user.role}</span>
            </div>
          )}
        </div>
      </div>
    </aside>
  )
}
