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
      }, 300)
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
    }, 300)
  }

  const isHealthy = health?.status === 'ok'

  return (
    <div className="login-page-container">
      {/* Barra superior flotante de la pantalla de login */}
      <div className="login-top-bar">
        <div className="backend-status-pill">
          <span className={`pulse-dot ${isHealthy ? '' : 'error'}`} />
          <span>{isHealthy ? 'FastAPI Backend Online' : 'FastAPI Offline'}</span>
          <span style={{ opacity: 0.4 }}>·</span>
          <span>{health?.accounts_loaded ?? 113} cuentas AD</span>
        </div>

        <button
          className="header-icon-btn"
          onClick={onToggleTheme}
          title={theme === 'dark' ? 'Cambiar a Modo Claro' : 'Cambiar a Modo Oscuro'}
          aria-label="Alternar tema"
        >
          {theme === 'dark' ? <Sun size={15} style={{ color: 'var(--warning)' }} /> : <Moon size={15} style={{ color: 'var(--primary)' }} />}
        </button>
      </div>

      <div className="login-content-grid">
        {/* PANEL IZQUIERDO: SHOWCASE CORPORATIVO Y CIBERSEGURIDAD (AJUSTADO SIN SCROLL) */}
        <div className="login-hero-panel">
          <div className="login-brand-header">
            <div className="brand-badge" style={{ width: '42px', height: '42px', fontSize: '16px' }}>
              C16
            </div>
            <div>
              <h1 className="login-brand-title">CASO16</h1>
              <span className="login-brand-sub">AI Security Command Center</span>
            </div>
          </div>

          <div className="login-hero-body">
            <div className="page-eyebrow" style={{ letterSpacing: '0.08em', fontSize: '10.5px' }}>
              ENTERPRISE IDENTITY THREAT INTELLIGENCE PLATFORM
            </div>
            <h2 className="login-headline">
              Detección de Cuentas Huérfanas, Privilegios Excesivos y{' '}
              <span className="gradient-text-cyber">Modelado Predictivo IA</span>
            </h2>
            <p className="login-subtext">
              Plataforma integral de ciberseguridad para auditoría determinista de Active Directory (R01–R06) y
              priorización de riesgos con modelos de Machine Learning M1 (Random Forest), M2 (XGBoost) y M3 (Isolation Forest).
            </p>

            {/* IMAGEN HERO COMPACTA CON CHIPS TELEMETRICOS INTEGRADAS */}
            <div className="login-showcase-container">
              <div className="login-image-card">
                <img
                  src="/caso16_login_hero.jpg"
                  alt="CASO16 Active Directory & AI Threat Visual"
                  className="login-hero-img"
                />
                <div className="login-image-overlay">
                  <div className="login-image-tag">
                    <span className="pulse-dot" />
                    <span>ITDR Active Directory · M1/M2/M3 AI Engine</span>
                  </div>
                </div>
              </div>

              {/* Tira compacta de métricas de telemetría */}
              <div className="login-metrics-strip-compact">
                <div className="cyber-metric-chip">
                  <Database size={12} style={{ color: 'var(--primary)' }} />
                  <span><strong>113</strong> Cuentas AD</span>
                </div>
                <div className="cyber-metric-chip">
                  <AlertTriangle size={12} style={{ color: 'var(--warning)' }} />
                  <span><strong>269</strong> Hallazgos (R01–R06)</span>
                </div>
                <div className="cyber-metric-chip">
                  <Cpu size={12} style={{ color: 'var(--secondary)' }} />
                  <span><strong>F1 = 0.941</strong> Optuna M2</span>
                </div>
                <div className="cyber-metric-chip">
                  <CheckCircle2 size={12} style={{ color: 'var(--success)' }} />
                  <span><strong>ISO 27001</strong> A.8.2</span>
                </div>
              </div>
            </div>

            {/* Tres pilares rápidos de capacidades */}
            <div className="login-capabilities-compact">
              <div className="login-cap-compact-item">
                <Database size={14} style={{ color: 'var(--primary)' }} />
                <span><strong>SharpHound AD:</strong> 4 dominios (PHANTOM, WRAITH, ESC1, GHOST).</span>
              </div>
              <div className="login-cap-compact-item">
                <Cpu size={14} style={{ color: 'var(--secondary)' }} />
                <span><strong>Laboratorio IA:</strong> Partición antifuga 70/15/15 y Optuna TPE.</span>
              </div>
              <div className="login-cap-compact-item">
                <FileCheck size={14} style={{ color: 'var(--success)' }} />
                <span><strong>Control ISO 27001:</strong> Evaluación analítica A.8.2 de privilegios.</span>
              </div>
            </div>
          </div>

          <div className="login-hero-footer">
            <span>© 2026 CASO16 Security AI · Entorno de demostración académica y evaluación SOC.</span>
          </div>
        </div>

        {/* PANEL DERECHO: FORMULARIO DE ACCESO (AJUSTADO 100% EN PANTALLA) */}
        <div className="login-form-panel">
          <div className="card login-form-card">
            <div className="login-card-header">
              <h3 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--foreground)', margin: 0 }}>
                Acceso al Command Center
              </h3>
              <p style={{ fontSize: '12px', color: 'var(--muted-foreground)', marginTop: '2px' }}>
                Haga clic en un rol para <strong>autocompletar e ingresar con 1 clic</strong>:
              </p>
            </div>

            {/* 4 BOTONES GRANDES DE ACCESO RÁPIDO CON AUTOCOMPLETADO */}
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
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="badge" style={{ background: 'var(--surface-elevated)', color: 'var(--primary)', border: '1px solid var(--border)', fontSize: '10px', padding: '2px 6px' }}>
                        {u.role === 'Superadministrador' ? '🛡️ Admin' : u.role === 'Analista de ciberseguridad' ? '🔍 SOC L2' : u.role === 'Auditor' ? '📋 Auditor' : '⚙️ MLOps'}
                      </span>
                      <span style={{ fontSize: '10.5px', color: 'var(--primary)', fontWeight: 600 }}>Entrar →</span>
                    </div>
                    <div style={{ marginTop: '5px' }}>
                      <strong style={{ fontSize: '12.5px', color: 'var(--foreground)', display: 'block' }}>{u.fullName}</strong>
                      <span style={{ fontSize: '10.5px', color: 'var(--muted-foreground)' }}>{u.email}</span>
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
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div>
                <label className="login-label">Correo Electrónico / Identidad</label>
                <div className="search-input-wrap">
                  <Mail size={14} />
                  <input
                    type="email"
                    className="search-input"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="usuario@caso16.security"
                    required
                    style={{ padding: '7px 12px 7px 34px', fontSize: '12.5px' }}
                  />
                </div>
              </div>

              <div>
                <label className="login-label">Contraseña</label>
                <div className="search-input-wrap" style={{ position: 'relative' }}>
                  <Lock size={14} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    className="search-input"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    required
                    style={{ padding: '7px 36px 7px 34px', fontSize: '12.5px' }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted-foreground)' }}
                    title={showPassword ? 'Ocultar' : 'Mostrar'}
                  >
                    {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
                style={{ padding: '10px', fontSize: '13px', marginTop: '4px', width: '100%' }}
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
    </div>
  )
}
