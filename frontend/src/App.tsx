import React, { useState, useEffect, useCallback } from 'react'
import {
  AuditLogItem,
  DashboardResponse,
  DirectoryAccount,
  DirectorySource,
  ExperimentJob,
  HealthResponse,
  NavItemKey,
  RemediationTicket,
  SecurityFinding,
  SecurityNotification,
  SecurityPolicy,
  SystemRole,
  SystemUser,
  ThemeMode,
  UserProfile,
  UserRole,
  DEMO_USERS,
} from './types'
import {
  getAccounts,
  getAuditLogs,
  getDashboard,
  getDirectories,
  getFindings,
  getHealth,
  getPolicies,
  getRoles,
  getTickets,
  getTrainingJobs,
  getUsers,
  getGeneralReportDownloadUrl,
} from './services/api'
import { Sidebar } from './components/layout/Sidebar'
import { Header } from './components/layout/Header'
import { SecurityOverview } from './features/dashboard/SecurityOverview'
import { IdentityInventory } from './features/identities/IdentityInventory'
import { AiTrainingCenter } from './features/training/AiTrainingCenter'
import { FindingsManagement } from './features/risk/FindingsManagement'
import { TicketsManagement } from './features/risk/TicketsManagement'
import { AuditTrail } from './features/audit/AuditTrail'
import { ReportCenter } from './features/reports/ReportCenter'
import { PoliciesAndUsers } from './features/admin/PoliciesAndUsers'
import { AutomationCenter } from './features/automation/AutomationCenter'
import { NotificationDrawer } from './components/notifications/NotificationDrawer'
import { LoginModal } from './components/auth/LoginModal'
import { Database, FileCode, CheckCircle, Info } from 'lucide-react'

const INITIAL_NOTIFICATIONS: SecurityNotification[] = [
  {
    id: 'notif-1',
    title: '58 Identidades en Alto Riesgo (Regla R06)',
    description: 'Cuentas con acumulación crítica de privilegios sin revisión semestral en PHANTOM.CORP y WRAITH.CORP.',
    timestamp: 'Hace 8 min',
    severity: 'critical',
    category: 'threat',
    read: false,
    targetNav: 'findings',
  },
  {
    id: 'notif-2',
    title: '81 Cuentas Huérfanas Inactivas (Regla R01)',
    description: 'Inactividad detectada ≥ 90 días. Se recomienda deshabilitación preventiva según control A.8.2.',
    timestamp: 'Hace 24 min',
    severity: 'high',
    category: 'orphan',
    read: false,
    targetNav: 'orphans',
  },
  {
    id: 'notif-3',
    title: '17 Cuentas SPN con Clave Eterna (Regla R04)',
    description: 'Cuentas de servicio con Password Never Expires activado propensas a ataques de Kerberoasting.',
    timestamp: 'Hace 1 hora',
    severity: 'medium',
    category: 'privilege',
    read: false,
    targetNav: 'excessive-privs',
  },
  {
    id: 'notif-4',
    title: 'Ticket TCK-2026-003 Próximo a Vencimiento',
    description: 'Revocación de Domain Admin en cuenta huérfana de soporte con SLA límite de 6 horas.',
    timestamp: 'Hace 2 horas',
    severity: 'high',
    category: 'ticket',
    read: false,
    targetNav: 'tickets',
  },
  {
    id: 'notif-5',
    title: 'Modelo M2 (XGBoost) Optimizado con Optuna',
    description: 'Estudio TPE completado con 10 trials y convergencia en F1-Score = 0.941 sobre conjunto de validación.',
    timestamp: 'Hace 3 horas',
    severity: 'info',
    category: 'ai',
    read: true,
    targetNav: 'ai-training-center',
  },
]

export function App() {
  const [theme, setTheme] = useState<ThemeMode>(() => {
    return (localStorage.getItem('caso16_theme') as ThemeMode) || 'dark'
  })
  const [currentNav, setCurrentNav] = useState<NavItemKey>('dashboard')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  // Estado de Usuario y Sesión RBAC
  const [user, setUser] = useState<UserProfile>(() => {
    try {
      const saved = localStorage.getItem('caso16_auth_user')
      if (saved) return JSON.parse(saved)
    } catch {
      // fallback
    }
    return DEMO_USERS.admin
  })

  // Modales y Notificaciones
  const [isLoginOpen, setIsLoginOpen] = useState(false)
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false)
  const [notifications, setNotifications] = useState<SecurityNotification[]>(INITIAL_NOTIFICATIONS)
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  // Datos en vivo del Backend
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loadingHealth, setLoadingHealth] = useState(false)
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [accounts, setAccounts] = useState<DirectoryAccount[]>([])
  const [findings, setFindings] = useState<SecurityFinding[]>([])
  const [tickets, setTickets] = useState<RemediationTicket[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([])
  const [policies, setPolicies] = useState<SecurityPolicy[]>([])
  const [directories, setDirectories] = useState<DirectorySource[]>([])
  const [users, setUsers] = useState<SystemUser[]>([])
  const [roles, setRoles] = useState<SystemRole[]>([])
  const [jobs, setJobs] = useState<ExperimentJob[]>([])

  // Efecto de tema
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('caso16_theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }

  // Toast feedback helper
  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => {
      setToastMessage(null)
    }, 3800)
  }

  // Cambio de rol directo (con sincronización total de perfil de usuario)
  const handleChangeRole = (newRole: UserRole) => {
    const matchingPreset = Object.values(DEMO_USERS).find((u) => u.role === newRole)
    const updatedUser: UserProfile = matchingPreset
      ? { ...matchingPreset }
      : { ...user, role: newRole }

    setUser(updatedUser)
    localStorage.setItem('caso16_auth_user', JSON.stringify(updatedUser))
    showToast(`Sesión conmutada a: ${updatedUser.fullName} (${newRole})`)
  }

  const handleLogin = (newUser: UserProfile) => {
    setUser(newUser)
    localStorage.setItem('caso16_auth_user', JSON.stringify(newUser))
    showToast(`Autenticado como: ${newUser.fullName} (${newUser.role})`)
  }

  // Manejo de Notificaciones
  const handleMarkAllNotificationsAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })))
    showToast('Todas las notificaciones han sido marcadas como leídas.')
  }

  const handleSelectNotification = (notif: SecurityNotification) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === notif.id ? { ...n, read: true } : n))
    )
    setIsNotificationsOpen(false)
    setCurrentNav(notif.targetNav)
  }

  const loadAllData = useCallback(async () => {
    setLoadingHealth(true)
    try {
      const [hRes, dRes, accRes, findRes, tRes, audRes, polRes, dirRes, uRes, rRes, jRes] =
        await Promise.allSettled([
          getHealth(),
          getDashboard(),
          getAccounts({ limit: 300 }),
          getFindings({ limit: 300 }),
          getTickets(),
          getAuditLogs(100),
          getPolicies(),
          getDirectories(),
          getUsers(),
          getRoles(),
          getTrainingJobs(),
        ])

      if (hRes.status === 'fulfilled') setHealth(hRes.value)
      if (dRes.status === 'fulfilled') setDashboard(dRes.value)
      if (accRes.status === 'fulfilled') setAccounts(accRes.value.items)
      if (findRes.status === 'fulfilled') setFindings(findRes.value.items)
      if (tRes.status === 'fulfilled') setTickets(tRes.value.items)
      if (audRes.status === 'fulfilled') setAuditLogs(audRes.value.items)
      if (polRes.status === 'fulfilled') setPolicies(polRes.value.items)
      if (dirRes.status === 'fulfilled') setDirectories(dirRes.value.items)
      if (uRes.status === 'fulfilled') setUsers(uRes.value.items)
      if (rRes.status === 'fulfilled') setRoles(rRes.value.items)
      if (jRes.status === 'fulfilled') setJobs(jRes.value.jobs)
    } catch (err) {
      console.error('Error sincronizando datos:', err)
    } finally {
      setLoadingHealth(false)
    }
  }, [])

  useEffect(() => {
    void loadAllData()
  }, [loadAllData])

  const handleExportGeneral = (format: 'pdf' | 'docx' | 'xlsx') => {
    window.open(getGeneralReportDownloadUrl(format), '_blank')
  }

  const unreadCount = notifications.filter((n) => !n.read).length

  return (
    <div className="command-center-app">
      {/* SIDEBAR NAVEGACIÓN — ESTRUCTURA SOC OPTIMIZADA */}
      <Sidebar
        currentNav={currentNav}
        onSelectNav={setCurrentNav}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        user={user}
        counts={{
          findings: findings.length || 269,
          orphans: dashboard?.inactive || 81,
          excessive: dashboard?.excessive || 64,
        }}
        onOpenLoginModal={() => setIsLoginOpen(true)}
      />

      {/* ÁREA PRINCIPAL */}
      <div className="main-wrapper">
        <Header
          currentNav={currentNav}
          theme={theme}
          onToggleTheme={toggleTheme}
          user={user}
          onChangeRole={handleChangeRole}
          health={health}
          loadingHealth={loadingHealth}
          onRefreshAll={loadAllData}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          unreadNotificationsCount={unreadCount}
          onOpenNotifications={() => setIsNotificationsOpen(true)}
          onOpenLoginModal={() => setIsLoginOpen(true)}
        />

        <main className="page-content">
          {/* 1. DASHBOARD OVERVIEW */}
          {(currentNav === 'dashboard' || currentNav === 'security-monitor') && (
            <SecurityOverview
              dashboard={dashboard}
              health={health}
              topAccounts={accounts}
              onSelectNav={setCurrentNav}
              onExportReport={handleExportGeneral}
              onRefresh={loadAllData}
            />
          )}

          {/* 2. GESTIÓN DE IDENTIDADES */}
          {currentNav === 'identities' && (
            <IdentityInventory
              accounts={accounts}
              filterType="all"
              onRefresh={loadAllData}
            />
          )}
          {currentNav === 'orphans' && (
            <IdentityInventory
              accounts={accounts}
              filterType="orphans"
              onRefresh={loadAllData}
            />
          )}
          {currentNav === 'excessive-privs' && (
            <IdentityInventory
              accounts={accounts}
              filterType="excessive"
              onRefresh={loadAllData}
            />
          )}
          {currentNav === 'directories' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div className="card">
                <div className="page-eyebrow">FUENTES DE IDENTIDAD ACTIVAS (M04)</div>
                <h2 className="page-title" style={{ fontSize: '24px' }}>Directorios Active Directory / LDAP</h2>
                <p className="page-desc" style={{ margin: '4px 0 16px' }}>
                  Conectores configurados sobre el Dataset de Telemetría SharpHound AD.
                </p>
                <div className="grid-cols-2">
                  {directories.map((dir) => (
                    <div key={dir.id} className="card" style={{ background: 'var(--surface-elevated)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                        <Database size={18} color="var(--primary)" />
                        <strong style={{ fontSize: '15px' }}>{dir.name}</strong>
                        <span className="badge success">{dir.status}</span>
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--muted-foreground)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <div>Dominio: <code>{dir.domain}</code></div>
                        <div>Servidor: <code>{dir.server_url}</code></div>
                        <div>Cuentas Sincronizadas: <strong>{dir.accounts_count}</strong></div>
                        <div>Última Sincronización: {new Date(dir.last_sync_at).toLocaleString('es-PE')}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 3. INTELIGENCIA ARTIFICIAL (M1, M2, M3, EDA, OPTUNA) */}
          {currentNav === 'ai-training-center' && <AiTrainingCenter initialTab="overview" />}

          {/* 4. GESTIÓN DE AMENAZAS & RIESGO */}
          {currentNav === 'findings' && (
            <FindingsManagement findings={findings} onRefresh={loadAllData} />
          )}
          {currentNav === 'tickets' && (
            <TicketsManagement tickets={tickets} onRefresh={loadAllData} />
          )}
          {currentNav === 'rules' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div className="card">
                <div className="page-eyebrow">CATÁLOGO DE AUDITORÍA REGULATORIA</div>
                <h2 className="page-title" style={{ fontSize: '24px' }}>Reglas de Detección Determinista (R01–R06)</h2>
                <p className="page-desc" style={{ margin: '4px 0 16px' }}>
                  Reglas matemáticas y lógicas verificables que fundamentan los hallazgos de seguridad sin opacidad.
                </p>
                <div className="grid-cols-2">
                  {[
                    { id: 'R01', name: 'Inactividad Prolongada', desc: 'Cuenta sin inicio de sesión durante 90 días o más (lastLogon / lastLogonTimestamp).', sev: 'Medio', iso: 'A.8.2' },
                    { id: 'R02', name: 'Privilegio Administrativo sin Justificación', desc: 'Cuenta perteneciente a grupos Domain Admins sin justificación formal verificada.', sev: 'Alto', iso: 'A.9.2' },
                    { id: 'R03', name: 'Cuenta Administrativa Duplicada', desc: 'Existencia de cuentas administrativas redundantes o clones sin supervisión.', sev: 'Medio', iso: 'A.9.2' },
                    { id: 'R04', name: 'Contraseña de Servicio no Expira', desc: 'Cuenta de tipo servicio con flag pwdNeverExpires activo.', sev: 'Alto', iso: 'A.9.4' },
                    { id: 'R05', name: 'Privilegios Inconsistentes', desc: 'Asignación de roles fuera de la política permitida de mínimo privilegio.', sev: 'Crítico', iso: 'A.8.2' },
                    { id: 'R06', name: 'Riesgo Alto sin Revisión', desc: 'Identidad con score de riesgo acumulado ≥ 60 sin revisión formal en más de 90 días.', sev: 'Alto', iso: 'A.9.4' },
                  ].map((rule) => (
                    <div key={rule.id} className="card" style={{ background: 'var(--surface-elevated)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <FileCode size={18} color="var(--primary)" />
                          <strong style={{ fontSize: '15px' }}>{rule.id}: {rule.name}</strong>
                        </div>
                        <span className={`badge ${rule.sev === 'Crítico' ? 'critical' : rule.sev === 'Alto' ? 'high' : 'medium'}`}>
                          {rule.sev}
                        </span>
                      </div>
                      <p style={{ fontSize: '12px', color: 'var(--muted-foreground)', lineHeight: 1.5, margin: 0 }}>
                        {rule.desc}
                      </p>
                      <div style={{ marginTop: '10px', fontSize: '11px', color: 'var(--muted-foreground)', opacity: 0.8, fontFamily: 'var(--font-mono)' }}>
                        Control de Seguridad: ISO/IEC 27001 {rule.iso}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 5. AUTOMATIZACIÓN & SOAR */}
          {currentNav === 'automation' && <AutomationCenter />}

          {/* 6. GOBIERNO, REPORTES Y AUDITORÍA */}
          {currentNav === 'reports' && <ReportCenter jobs={jobs} />}
          {currentNav === 'audit' && <AuditTrail logs={auditLogs} />}
          {currentNav === 'policies' && (
            <PoliciesAndUsers
              policies={policies}
              users={users}
              roles={roles}
              onRefresh={loadAllData}
            />
          )}
        </main>
      </div>

      {/* DRAWER LATERAL DE NOTIFICACIONES */}
      <NotificationDrawer
        isOpen={isNotificationsOpen}
        onClose={() => setIsNotificationsOpen(false)}
        notifications={notifications}
        onMarkAllAsRead={handleMarkAllNotificationsAsRead}
        onSelectNotification={handleSelectNotification}
      />

      {/* MODAL DE LOGIN & SELECCIÓN DE ROL */}
      <LoginModal
        isOpen={isLoginOpen}
        onClose={() => setIsLoginOpen(false)}
        currentUser={user}
        onLogin={handleLogin}
      />

      {/* TOAST DE FEEDBACK OPERATIVO */}
      {toastMessage && (
        <div className="floating-toast">
          <CheckCircle size={16} style={{ color: 'var(--success)' }} />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  )
}

export default App
