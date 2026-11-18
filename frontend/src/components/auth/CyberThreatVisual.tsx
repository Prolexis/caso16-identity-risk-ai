import React from 'react'
import { Shield, Database, Cpu, Activity, AlertTriangle, Lock, CheckCircle2 } from 'lucide-react'

export const CyberThreatVisual: React.FC = () => {
  return (
    <div className="cyber-visual-wrapper">
      {/* HUD Telemetry Header */}
      <div className="cyber-visual-hud-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="pulse-dot" />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: 600, color: 'var(--primary)', letterSpacing: '0.06em' }}>
            ITDR THREAT GRAPH · LIVE TOPOLOGY
          </span>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <span className="badge" style={{ background: 'var(--surface)', fontSize: '10px', border: '1px solid var(--border)' }}>
            SharpHound AD Telemetry
          </span>
        </div>
      </div>

      {/* SVG Vector Topology Graph */}
      <div className="cyber-visual-canvas">
        <svg viewBox="0 0 540 260" className="cyber-svg-graph" preserveAspectRatio="xMidYMid meet">
          <defs>
            <linearGradient id="cyberCyanGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#38BDF8" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#087EA4" stopOpacity="0.3" />
            </linearGradient>
            <linearGradient id="cyberPurpleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#818CF8" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#4F46E5" stopOpacity="0.3" />
            </linearGradient>
            <linearGradient id="cyberDangerGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#F43F5E" stopOpacity="0.9" />
              <stop offset="100%" stopColor="#BE123C" stopOpacity="0.4" />
            </linearGradient>
            <radialGradient id="centralGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#38BDF8" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#38BDF8" stopOpacity="0" />
            </radialGradient>
            <filter id="glowEffect" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Background Ambient Glow */}
          <circle cx="270" cy="130" r="100" fill="url(#centralGlow)" />

          {/* Connection Lines (AD Domains to Central AI Engine) */}
          <g stroke="var(--border)" strokeWidth="1.5" strokeDasharray="3 3" opacity="0.6">
            <line x1="80" y1="50" x2="270" y2="130" />
            <line x1="80" y1="210" x2="270" y2="130" />
            <line x1="460" y1="50" x2="270" y2="130" />
            <line x1="460" y1="210" x2="270" y2="130" />
          </g>

          {/* Dynamic Telemetry Rays */}
          <g stroke="var(--primary)" strokeWidth="1.8" opacity="0.8">
            <line x1="160" y1="85" x2="220" y2="110" strokeLinecap="round" />
            <line x1="160" y1="175" x2="220" y2="150" strokeLinecap="round" />
            <line x1="380" y1="85" x2="320" y2="110" strokeLinecap="round" />
            <line x1="380" y1="175" x2="320" y2="150" strokeLinecap="round" />
          </g>

          {/* Domain Node 1: PHANTOM.CORP */}
          <g transform="translate(80, 50)" className="graph-node-group">
            <circle r="22" fill="var(--surface)" stroke="var(--primary)" strokeWidth="1.5" filter="url(#glowEffect)" />
            <circle r="4" fill="var(--primary)" />
            <text y="-28" textAnchor="middle" fill="var(--foreground)" fontSize="11" fontWeight="700" fontFamily="var(--font-sans)">
              PHANTOM.CORP
            </text>
            <text y="36" textAnchor="middle" fill="var(--muted-foreground)" fontSize="9.5" fontFamily="var(--font-mono)">
              48 identidades
            </text>
          </g>

          {/* Domain Node 2: WRAITH.CORP */}
          <g transform="translate(80, 210)" className="graph-node-group">
            <circle r="22" fill="var(--surface)" stroke="var(--secondary)" strokeWidth="1.5" />
            <circle r="4" fill="var(--secondary)" />
            <text y="38" textAnchor="middle" fill="var(--foreground)" fontSize="11" fontWeight="700" fontFamily="var(--font-sans)">
              WRAITH.CORP
            </text>
            <text y="-28" textAnchor="middle" fill="var(--muted-foreground)" fontSize="9.5" fontFamily="var(--font-mono)">
              34 identidades
            </text>
          </g>

          {/* Domain Node 3: ESC1.LOCAL */}
          <g transform="translate(460, 50)" className="graph-node-group">
            <circle r="22" fill="var(--surface)" stroke="var(--warning)" strokeWidth="1.5" />
            <circle r="4" fill="var(--warning)" />
            <text y="-28" textAnchor="middle" fill="var(--foreground)" fontSize="11" fontWeight="700" fontFamily="var(--font-sans)">
              ESC1.LOCAL
            </text>
            <text y="36" textAnchor="middle" fill="var(--muted-foreground)" fontSize="9.5" fontFamily="var(--font-mono)">
              18 identidades
            </text>
          </g>

          {/* Domain Node 4: GHOST.CORP */}
          <g transform="translate(460, 210)" className="graph-node-group">
            <circle r="22" fill="var(--surface)" stroke="var(--destructive)" strokeWidth="1.5" />
            <circle r="4" fill="var(--destructive)" />
            <text y="38" textAnchor="middle" fill="var(--foreground)" fontSize="11" fontWeight="700" fontFamily="var(--font-sans)">
              GHOST.CORP
            </text>
            <text y="-28" textAnchor="middle" fill="var(--muted-foreground)" fontSize="9.5" fontFamily="var(--font-mono)">
              13 identidades
            </text>
          </g>

          {/* Central AI Engine Node (M1 · M2 · M3) */}
          <g transform="translate(270, 130)" className="graph-node-group">
            <circle r="42" fill="var(--surface)" stroke="var(--primary)" strokeWidth="2.5" filter="url(#glowEffect)" />
            <circle r="36" fill="var(--surface-elevated)" opacity="0.9" />
            <text y="-6" textAnchor="middle" fill="var(--foreground)" fontSize="12" fontWeight="800" fontFamily="var(--font-sans)">
              AI ENGINE
            </text>
            <text y="12" textAnchor="middle" fill="var(--primary)" fontSize="10" fontWeight="700" fontFamily="var(--font-mono)">
              M1 · M2 · M3
            </text>
          </g>

          {/* Satellite Risk Badges */}
          <g transform="translate(270, 42)">
            <rect x="-65" y="-12" width="130" height="24" rx="12" fill="var(--surface)" stroke="var(--destructive)" strokeWidth="1" />
            <circle cx="-50" cy="0" r="3.5" fill="var(--destructive)" />
            <text x="5" y="4" textAnchor="middle" fill="var(--destructive)" fontSize="10" fontWeight="700" fontFamily="var(--font-sans)">
              58 Riesgo Crítico (R06)
            </text>
          </g>

          <g transform="translate(270, 222)">
            <rect x="-65" y="-12" width="130" height="24" rx="12" fill="var(--surface)" stroke="var(--warning)" strokeWidth="1" />
            <circle cx="-50" cy="0" r="3.5" fill="var(--warning)" />
            <text x="5" y="4" textAnchor="middle" fill="var(--warning)" fontSize="10" fontWeight="700" fontFamily="var(--font-sans)">
              81 Huérfanas (R01)
            </text>
          </g>
        </svg>
      </div>

      {/* Floating Metrics Pill Strip */}
      <div className="cyber-visual-metrics-strip">
        <div className="cyber-metric-chip">
          <Database size={13} style={{ color: 'var(--primary)' }} />
          <span><strong>113</strong> Cuentas AD</span>
        </div>
        <div className="cyber-metric-chip">
          <AlertTriangle size={13} style={{ color: 'var(--warning)' }} />
          <span><strong>269</strong> Hallazgos (R01–R06)</span>
        </div>
        <div className="cyber-metric-chip">
          <Cpu size={13} style={{ color: 'var(--secondary)' }} />
          <span><strong>F1 = 0.941</strong> Optuna M2</span>
        </div>
        <div className="cyber-metric-chip">
          <CheckCircle2 size={13} style={{ color: 'var(--success)' }} />
          <span><strong>ISO 27001</strong> A.8.2</span>
        </div>
      </div>
    </div>
  )
}
