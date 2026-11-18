import React, { useState } from 'react'
import {
  Shield,
  Lock,
  Mail,
  User,
  CheckCircle,
  X,
  ArrowRight,
  Sparkles,
} from 'lucide-react'
import { DEMO_USERS, UserProfile, UserRole } from '../../types'

interface LoginModalProps {
  isOpen: boolean
  onClose: () => void
  currentUser: UserProfile
  onLogin: (user: UserProfile) => void
}

export const LoginModal: React.FC<LoginModalProps> = ({
  isOpen,
  onClose,
  currentUser,
  onLogin,
}) => {
  const [email, setEmail] = useState(currentUser.email)
  const [password, setPassword] = useState('••••••••••••')
  const [selectedPresetKey, setSelectedPresetKey] = useState<string>('admin')

  if (!isOpen) return null

  const handleSelectPreset = (key: string) => {
    setSelectedPresetKey(key)
    const preset = DEMO_USERS[key]
    if (preset) {
      setEmail(preset.email)
      setPassword('Security2026!')
    }
  }

  const handleFastLogin = (key: string) => {
    const preset = DEMO_USERS[key]
    if (preset) {
      onLogin({
        username: preset.username,
        email: preset.email,
        fullName: preset.fullName,
        role: preset.role,
        avatarInitials: preset.avatarInitials,
      })
      onClose()
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const preset = DEMO_USERS[selectedPresetKey] || DEMO_USERS.admin
    onLogin({
      username: email,
      email: email,
      fullName: preset.fullName,
      role: preset.role,
      avatarInitials: preset.avatarInitials,
    })
    onClose()
  }

  return (
    <div className="drawer-backdrop" onClick={onClose} style={{ alignItems: 'center', justifyContent: 'center' }}>
      <div
        className="card"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: '520px',
          padding: '28px 32px',
          boxShadow: 'var(--shadow-lg)',
          animation: 'fadeIn 0.2s ease-out',
          position: 'relative',
        }}
      >
        <button
          className="header-icon-btn"
          onClick={onClose}
          style={{ position: 'absolute', top: '18px', right: '18px' }}
          aria-label="Cerrar modal"
        >
          <X size={16} />
        </button>

        {/* Brand Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
          <div className="brand-badge" style={{ width: '40px', height: '40px', fontSize: '15px' }}>
            C16
          </div>
          <div>
            <div className="page-eyebrow">ENTERPRISE ACCESS CONTROL</div>
            <h3 style={{ margin: '2px 0 0', fontSize: '19px', color: 'var(--foreground)' }}>
              Autenticación & Selección de Rol RBAC
            </h3>
          </div>
        </div>

        <p style={{ fontSize: '13px', color: 'var(--muted-foreground)', marginBottom: '20px', lineHeight: 1.45 }}>
          Seleccione una cuenta de demostración con <strong>1 clic</strong> o ingrese credenciales corporativas para conmutar permisos y privilegios del sistema.
        </p>

        {/* Acceso Rápido Autocompletado */}
        <div style={{ marginBottom: '20px' }}>
          <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--muted-foreground)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Acceso Rápido Autocompletado (Selección Directa)
          </span>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '10px' }}>
            {Object.entries(DEMO_USERS).map(([key, u]) => {
              const isCurrent = currentUser.role === u.role
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => handleFastLogin(key)}
                  className="btn btn-secondary"
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    padding: '12px 14px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid',
                    borderColor: isCurrent ? 'var(--primary)' : 'var(--border)',
                    background: isCurrent ? 'var(--surface-elevated)' : 'var(--surface)',
                    textAlign: 'left',
                    gap: '4px',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                    <strong style={{ fontSize: '12.5px', color: 'var(--foreground)' }}>{u.fullName}</strong>
                    {isCurrent && <CheckCircle size={14} style={{ color: 'var(--primary)' }} />}
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--primary)', fontWeight: 500 }}>
                    {u.role}
                  </span>
                  <span style={{ fontSize: '10px', color: 'var(--muted-foreground)' }}>
                    {u.email}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Formulario Manual */}
        <form onSubmit={handleSubmit} style={{ borderTop: '1px solid var(--border)', paddingTop: '18px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <label style={{ fontSize: '12px', fontWeight: 500, color: 'var(--muted-foreground)', display: 'block', marginBottom: '4px' }}>
                Correo Corporativo
              </label>
              <div className="search-input-wrap">
                <Mail size={14} />
                <input
                  type="email"
                  className="search-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="usuario@caso16.security"
                  required
                />
              </div>
            </div>

            <div>
              <label style={{ fontSize: '12px', fontWeight: 500, color: 'var(--muted-foreground)', display: 'block', marginBottom: '4px' }}>
                Contraseña
              </label>
              <div className="search-input-wrap">
                <Lock size={14} />
                <input
                  type="password"
                  className="search-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                />
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
              <button type="button" className="btn btn-secondary" onClick={onClose}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-primary">
                Iniciar Sesión <ArrowRight size={14} />
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}
