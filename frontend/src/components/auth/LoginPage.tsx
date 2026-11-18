import React, { useState } from 'react'
import {
  Shield,
  Lock,
  Mail,
  ArrowRight,
  Eye,
  EyeOff,
  Sun,
  Moon,
  Database,
  Cpu,
  FileCheck,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react'
import { DEMO_USERS, HealthResponse, ThemeMode, UserProfile } from '../../types'

interface LoginPageProps {
  onLogin: (user: UserProfile) => void
  health?: HealthResponse | null
  theme: ThemeMode
  onToggleTheme: () => void
}

export const LoginPage: React.FC<LoginPageProps> = ({
  onLogin,
  health,
  theme,
  onToggleTheme,
}) => {
  const [selectedKey, setSelectedKey] = useState<string>('admin')
  const [email, setEmail] = useState<string>(DEMO_USERS.admin.email)
  const [password, setPassword] = useState<string>('AdminSOC2026!')
  const [showPassword, setShowPassword] = useState<boolean>(false)
  const [loading, setLoading] = useState<boolean>(false)

  const handleSelectPreset = (key: string) => {
    setSelectedKey(key)
    const preset = DEMO_USERS[key]
    if (preset) {
      setEmail(preset.email)
      setPassword(`${key}Pass2026!`)
    }
  }

  const handleDirectAccess = (key: string) => {
    handleSelectPreset(key)
    const preset = DEMO_USERS[key]
    if (preset) {
      setLoading(true)
      setTimeout(() => {
        onLogin({
          username: preset.username,
          email: preset.email,
          fullName: preset.fullName,
          role: preset.role,
          avatarInitials: preset.avatarInitials,
        })
      }, 250)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setTimeout(() => {
      const preset = DEMO_USERS[selectedKey] || DEMO_USERS.admin
      onLogin({
        username: email,
        email: email,
        fullName: preset.fullName,
        role: preset.role,
        avatarInitials: preset.avatarInitials,
      })
    }, 250)
  }

  const isHealthy = health?.status === 'ok'

  return (
    <div className="login-page-container">
      {/* 1. BARRA SUPERIOR ESTRUCTURADA Y ALINEADA */}
      <header className="login-header-bar">
        <div className="login-header-brand">
          <div className="brand-badge" style={{ width: '38px', height: '38px', fontSize: '15px' }}>
            C16
          </div>
          <div className="login-brand-meta">
            <span className="login-brand-title">CASO16</span>
            <span className="login-brand-sep">/</span>
            <span className="login-brand-sub">AI Security Command Center</span>
          </div>
        </div>

        <div className="login-header-tools">
          <div className="backend-status-pill">
            <span className={`pulse-dot ${isHealthy ? '' : 'error'}`} />
            <span>{isHealthy ? 'FastAPI Backend Online' : 'FastAPI Offline'}</span>
            <span style={{ opacity: 0.35 }}>·</span>
            <span>{health?.accounts_loaded ?? 113} cuentas AD</span>
          </div>

          <button
            className="header-icon-btn"
            onClick={onToggleTheme}
            title={theme === 'dark' ? 'Cambiar a Modo Claro' : 'Cambiar a Modo Oscuro'}
            aria-label="Alternar tema"
          >
            {theme === 'dark' ? <Sun size={16} style={{ color: 'var(--warning)' }} /> : <Moon size={16} style={{ color: 'var(--primary)' }} />}
          </button>
        </div>
      </header>

      {/* 2. ESCENARIO CENTRAL PROMINENTE Y EQUILIBRADO */}
      <main className="login-main-stage">
        <div className="login-stage-container">
          {/* PANEL IZQUIERDO: SHOWCASE CORPORATIVO */}
          <div className="login-hero-panel">
            <div className="page-eyebrow" style={{ letterSpacing: '0.08em', fontSize: '11.5px', marginBottom: '6px' }}>
              ENTERPRISE IDENTITY THREAT INTELLIGENCE
            </div>
            <h1 className="login-headline">
              Detección de Cuentas Huérfanas, Privilegios Excesivos y{' '}
              <span className="gradient-text-cyber">Modelado IA</span>
            </h1>
            <p className="login-subtext">
              Plataforma integral de ciberseguridad para auditoría determinista de Active Directory (R01–R06) y
              priorización de riesgos con Machine Learning M1 (Random Forest), M2 (XGBoost) y M3 (Isolation Forest).
            </p>

            {/* IMAGEN HERO PROMINENTE */}
            <div className="login-image-card">
              <img
                src="/caso16_login_hero.jpg"
                alt="CASO16 Active Directory & AI Threat Visual"
                className="login-hero-img"
              />
              <div className="login-image-overlay">
                <div className="login-image-tag">
                  <span className="pulse-dot" />
                  <span>ITDR Active Directory · Topología Multi-Dominio</span>
                </div>
              </div>
            </div>

            {/* TIRA DE MÉTRICAS */}
            <div className="login-metrics-grid">
              <div className="cyber-metric-chip">
                <Database size={14} style={{ color: 'var(--primary)' }} />
                <span><strong>113</strong> Cuentas AD</span>
              </div>
              <div className="cyber-metric-chip">
                <AlertTriangle size={14} style={{ color: 'var(--warning)' }} />
                <span><strong>269</strong> Hallazgos (R01–R06)</span>
              </div>
              <div className="cyber-metric-chip">
                <Cpu size={14} style={{ color: 'var(--secondary)' }} />
                <span><strong>F1 = 0.941</strong> Optuna M2</span>
              </div>
              <div className="cyber-metric-chip">
                <CheckCircle2 size={14} style={{ color: 'var(--success)' }} />
                <span><strong>ISO 27001</strong> A.8.2</span>
              </div>
            </div>

            {/* TRES PILARES RÁPIDOS */}
            <div className="login-capabilities-compact">
              <div className="login-cap-compact-item">
                <span className="cap-bullet-icon"><Database size={13} style={{ color: 'var(--primary)' }} /></span>
                <span><strong>SharpHound AD:</strong> 4 dominios integrados (PHANTOM, WRAITH, GHOST, ESC1).</span>
              </div>
              <div className="login-cap-compact-item">
                <span className="cap-bullet-icon"><Cpu size={13} style={{ color: 'var(--secondary)' }} /></span>
                <span><strong>Laboratorio IA:</strong> Partición 70/15/15 sin fuga y optimización bayesiana TPE.</span>
              </div>
              <div className="login-cap-compact-item">
                <span className="cap-bullet-icon"><FileCheck size={13} style={{ color: 'var(--success)' }} /></span>
                <span><strong>Control ISO:</strong> Evaluación continua de derechos de acceso privilegiado.</span>
              </div>
            </div>
          </div>

          {/* PANEL DERECHO: FORMULARIO DE ACCESO PROMINENTE */}
          <div className="login-form-panel">
            <div className="card login-form-card">
              <div className="login-card-header">
                <h2 style={{ fontSize: '21px', fontWeight: 700, color: 'var(--foreground)', margin: 0 }}>
                  Acceso al Command Center
                </h2>
                <p style={{ fontSize: '12px', color: 'var(--muted-foreground)', marginTop: '4px', marginBottom: 0 }}>
                  Haga clic en un rol para <strong>autocompletar e ingresar con 1 clic</strong>:
                </p>
              </div>

              {/* 4 BOTONES DE ACCESO RÁPIDO */}
              <div className="login-presets-container">
                {Object.entries(DEMO_USERS).map(([key, u]) => {
                  const isSelected = selectedKey === key
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => handleDirectAccess(key)}
                      className={`login-preset-card ${isSelected ? 'selected' : ''}`}
                      title={`Acceso inmediato como ${u.fullName}`}
                    >
                      <div className="preset-card-top">
                        <span className="preset-role-badge">
                          {u.role === 'Superadministrador' ? '🛡️ Admin' : u.role === 'Analista de ciberseguridad' ? '🔍 SOC L2' : u.role === 'Auditor' ? '📋 Auditor' : '⚙️ MLOps'}
                        </span>
                        <span className="preset-enter-link">Entrar →</span>
                      </div>
                      <div className="preset-card-bottom">
                        <strong className="preset-user-name">{u.fullName}</strong>
                        <span className="preset-user-email">{u.email}</span>
                      </div>
                    </button>
                  )
                })}
              </div>

              {/* SEPARADOR */}
              <div className="login-divider">
                <span>O ingrese credenciales manualmente</span>
              </div>

              {/* FORMULARIO */}
              <form onSubmit={handleSubmit} className="login-form-fields">
                <div>
                  <label className="login-label">Correo Electrónico / Identidad</label>
                  <div className="search-input-wrap">
                    <Mail size={15} />
                    <input
                      type="email"
                      className="search-input"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="usuario@caso16.security"
                      required
                      style={{ padding: '8px 12px 8px 36px', fontSize: '13px' }}
                    />
                  </div>
                </div>

                <div>
                  <label className="login-label">Contraseña</label>
                  <div className="search-input-wrap" style={{ position: 'relative' }}>
                    <Lock size={15} />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      className="search-input"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      required
                      style={{ padding: '8px 38px 8px 36px', fontSize: '13px' }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="password-eye-btn"
                      title={showPassword ? 'Ocultar' : 'Mostrar'}
                    >
                      {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={loading}
                  style={{ padding: '11px 16px', fontSize: '13.5px', marginTop: '3px', width: '100%', fontWeight: 600 }}
                >
                  {loading ? 'Accediendo al Command Center...' : 'Entrar al Command Center'}
                  {!loading && <ArrowRight size={15} />}
                </button>
              </form>

              <div className="login-security-notice">
                <Shield size={13} style={{ color: 'var(--primary)' }} />
                <span>Autenticación RBAC estricta · Sesión protegida y registrada en auditoría</span>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* 3. FOOTER GLOBAL ALINEADO */}
      <footer className="login-global-footer">
        <span>© 2026 CASO16 Security AI · Entorno de demostración académica y evaluación SOC</span>
        <span className="footer-dot">·</span>
        <span>Active Directory ITDR</span>
        <span className="footer-dot">·</span>
        <span>Modelos M1/M2/M3</span>
      </footer>
    </div>
  )
}
