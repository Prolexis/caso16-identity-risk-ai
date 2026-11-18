import React, { useState, useEffect, useCallback } from 'react'
import {
  Cpu,
  LineChart,
  Sliders,
  PlayCircle,
  FileCheck,
  Scale,
  BrainCircuit,
  FileSpreadsheet,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Square,
  RefreshCw,
  Download,
  Info,
  Layers,
  BarChart2,
  Sparkles,
} from 'lucide-react'
import {
  EdaSummary,
  ExperimentJob,
  TrainingDefaultsConfig,
} from '../../types'
import {
  cancelTrainingJob,
  getEda,
  getTrainingDefaults,
  getTrainingJobDetail,
  getTrainingJobs,
  getTrainingReportDownloadUrl,
  startTrainingExperiment,
} from '../../services/api'

type SubTab =
  | 'overview'
  | 'eda'
  | 'preprocessing'
  | 'configuration'
  | 'execution'
  | 'evaluation'
  | 'comparison'
  | 'reports'

interface AiTrainingCenterProps {
  initialTab?: SubTab
}

export const AiTrainingCenter: React.FC<AiTrainingCenterProps> = ({ initialTab = 'overview' }) => {
  const [activeTab, setActiveTab] = useState<SubTab>(initialTab)
  const [useDemoDataset, setUseDemoDataset] = useState(false)
  const [edaData, setEdaData] = useState<EdaSummary | null>(null)
  const [loadingEda, setLoadingEda] = useState(false)
  const [defaults, setDefaults] = useState<TrainingDefaultsConfig | null>(null)
  const [jobs, setJobs] = useState<ExperimentJob[]>([])
  const [selectedJob, setSelectedJob] = useState<ExperimentJob | null>(null)
  const [isExecuting, setIsExecuting] = useState(false)
  const [statusMsg, setStatusMsg] = useState<string | null>(null)

  // Hiperparámetros M1
  const [runM1, setRunM1] = useState(true)
  const [m1Estimators, setM1Estimators] = useState(300)
  const [m1MaxDepth, setM1MaxDepth] = useState(12)
  const [m1MinLeaf, setM1MinLeaf] = useState(2)
  const [m1ClassWeight, setM1ClassWeight] = useState('balanced')

  // Hiperparámetros M2
  const [runM2, setRunM2] = useState(true)
  const [m2Estimators, setM2Estimators] = useState(300)
  const [m2MaxDepth, setM2MaxDepth] = useState(5)
  const [m2LearningRate, setM2LearningRate] = useState(0.05)
  const [m2EarlyStopping, setM2EarlyStopping] = useState(30)
  const [m2Subsample, setM2Subsample] = useState(0.8)

  // Hiperparámetros M3
  const [runM3, setRunM3] = useState(true)
  const [m3Estimators, setM3Estimators] = useState(300)
  const [m3Contamination, setM3Contamination] = useState('auto')
  const [m3MaxFeatures, setM3MaxFeatures] = useState(1.0)

  // Optuna & Global
  const [useOptuna, setUseOptuna] = useState(true)
  const [optunaTrialsM1, setOptunaTrialsM1] = useState(10)
  const [optunaTrialsM2, setOptunaTrialsM2] = useState(10)
  const [optunaTrialsM3, setOptunaTrialsM3] = useState(8)
  const [seed, setSeed] = useState(42)

  // Cargar EDA
  const loadEda = useCallback(async (demo: boolean) => {
    setLoadingEda(true)
    try {
      const data = await getEda(demo)
      setEdaData(data)
    } catch (err) {
      console.error('Error cargando EDA:', err)
    } finally {
      setLoadingEda(false)
    }
  }, [])

  // Cargar defaults y lista de experimentos
  const loadJobsAndDefaults = useCallback(async () => {
    try {
      const [defs, jobsRes] = await Promise.all([getTrainingDefaults(), getTrainingJobs()])
      setDefaults(defs)
      setJobs(jobsRes.jobs)
      if (jobsRes.jobs.length > 0) {
        const latest = jobsRes.jobs[0]
        const full = await getTrainingJobDetail(latest.job_id)
        setSelectedJob(full)
      }
    } catch (err) {
      console.error('Error cargando jobs:', err)
    }
  }, [])

  useEffect(() => {
    void loadEda(useDemoDataset)
    void loadJobsAndDefaults()
  }, [loadEda, loadJobsAndDefaults, useDemoDataset])

  // Polling de job en ejecución
  useEffect(() => {
    if (!isExecuting && (!selectedJob || selectedJob.status !== 'running')) return
    const interval = setInterval(async () => {
      if (!selectedJob) return
      try {
        const updated = await getTrainingJobDetail(selectedJob.job_id)
        setSelectedJob(updated)
        if (updated.status === 'completed' || updated.status === 'failed' || updated.status === 'cancelled') {
          setIsExecuting(false)
          const jRes = await getTrainingJobs()
          setJobs(jRes.jobs)
        }
      } catch (err) {
        console.error('Error polling:', err)
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [isExecuting, selectedJob])

  const handleStartExperiment = async () => {
    setIsExecuting(true)
    setStatusMsg('Iniciando pipeline de entrenamiento y optimización...')
    try {
      const res = await startTrainingExperiment({
        run_m1: runM1,
        run_m2: runM2,
        run_m3: runM3,
        use_optuna: useOptuna,
        optuna_trials_m1: optunaTrialsM1,
        optuna_trials_m2: optunaTrialsM2,
        optuna_trials_m3: optunaTrialsM3,
        seed,
        use_demo_dataset: useDemoDataset,
        params_m1: {
          n_estimators: m1Estimators,
          max_depth: m1MaxDepth,
          min_samples_leaf: m1MinLeaf,
          class_weight: m1ClassWeight,
        },
        params_m2: {
          n_estimators: m2Estimators,
          max_depth: m2MaxDepth,
          learning_rate: m2LearningRate,
          early_stopping_rounds: m2EarlyStopping,
          subsample: m2Subsample,
        },
        params_m3: {
          n_estimators: m3Estimators,
          contamination: m3Contamination === 'auto' ? 'auto' : parseFloat(m3Contamination),
          max_features: m3MaxFeatures,
        },
      })
      setStatusMsg(`Experimento lanzado exitosamente: ${res.job_id}`)
      setActiveTab('execution')
      const full = await getTrainingJobDetail(res.job_id)
      setSelectedJob(full)
      const jRes = await getTrainingJobs()
      setJobs(jRes.jobs)
    } catch (err: unknown) {
      setIsExecuting(false)
      setStatusMsg(`Error al iniciar: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  const handleCancel = async () => {
    if (!selectedJob) return
    try {
      await cancelTrainingJob(selectedJob.job_id)
      setStatusMsg('Señal de parada enviada.')
    } catch (err: unknown) {
      setStatusMsg(`Error cancelando: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* HEADER DEL CENTRO DE ENTRENAMIENTO */}
      <div className="page-hero-banner">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div className="page-eyebrow">LABORATORIO MLOps & MODELOS INTELIGENTES</div>
            <h1 className="page-title">AI Model Training Center</h1>
            <p className="page-desc">
              Entrenamiento riguroso, optimización con Optuna, evaluación ciega (Blind Test 15%) y auditoría de M1 (Random Forest), M2 (XGBoost) y M3 (Isolation Forest).
            </p>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', color: 'var(--text-main)' }}>
              <input
                type="checkbox"
                checked={useDemoDataset}
                onChange={(e) => setUseDemoDataset(e.target.checked)}
              />
              <span>{useDemoDataset ? 'Dataset Sintético (Docencia)' : 'Dataset SharpHound AD Real (113 cuentas)'}</span>
            </label>
            <button
              className="btn btn-primary"
              onClick={handleStartExperiment}
              disabled={isExecuting}
            >
              <PlayCircle size={16} />
              {isExecuting ? 'Optimizando...' : 'Iniciar Entrenamiento'}
            </button>
          </div>
        </div>
      </div>

      {statusMsg && (
        <div style={{ padding: '10px 16px', background: 'rgba(34,211,238,0.15)', border: '1px solid rgba(34,211,238,0.4)', borderRadius: 'var(--radius-sm)', color: '#22D3EE', fontSize: '13px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>ℹ {statusMsg}</span>
          <button style={{ background: 'none', border: 'none', color: '#22D3EE', cursor: 'pointer' }} onClick={() => setStatusMsg(null)}>✕</button>
        </div>
      )}

      {/* PESTAÑAS DE NAVEGACIÓN INTERNA */}
      <div style={{ display: 'flex', gap: '6px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px', overflowX: 'auto' }}>
        {[
          { id: 'overview', label: '1. Pipeline & Metodología', icon: Layers },
          { id: 'eda', label: '2. Exploración EDA', icon: LineChart },
          { id: 'preprocessing', label: '3. Preproceso & Partición', icon: Sparkles },
          { id: 'configuration', label: '4. Configuración M1/M2/M3', icon: Sliders },
          { id: 'execution', label: '5. Consola & Optuna', icon: PlayCircle },
          { id: 'evaluation', label: '6. Métricas & Validación', icon: FileCheck },
          { id: 'comparison', label: '7. Comparación de Modelos', icon: Scale },
          { id: 'reports', label: '8. Reportes & Trazabilidad', icon: FileSpreadsheet },
        ].map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as SubTab)}
              className="btn"
              style={{
                background: isActive ? 'var(--bg-elevated)' : 'transparent',
                color: isActive ? 'var(--color-primary)' : 'var(--text-muted)',
                borderColor: isActive ? 'var(--border-highlight)' : 'transparent',
                fontSize: '12px',
                padding: '8px 14px',
                whiteSpace: 'nowrap',
              }}
            >
              <Icon size={14} />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* 1. OVERVIEW & PIPELINE METODOLÓGICO */}
      {activeTab === 'overview' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="card">
            <h3 className="card-title" style={{ color: 'var(--color-primary)', marginBottom: '8px' }}>
              Ciclo Metodológico Completo del Entrenamiento
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '20px' }}>
              Garantiza trazabilidad y reproducibilidad científica: la división 70/15/15 aísla estrictamente el conjunto de prueba ciego, evitando fuga de datos en la imputación y en la búsqueda de hiperparámetros.
            </p>

            {/* Diagrama de Fases */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px', overflowX: 'auto', padding: '12px 6px' }}>
              {[
                { num: '01', title: 'Datos AD/LDAP', desc: '113 cuentas + membresías', status: 'Listo' },
                { num: '02', title: 'EDA & Calidad', desc: 'Outliers, nulos, AD lag', status: 'Activo' },
                { num: '03', title: 'Preprocesamiento', desc: 'Imputación solo en Train', status: 'Antifuga' },
                { num: '04', title: 'Partición 70/15/15', desc: '15% Test ciego reservado', status: 'Blind' },
                { num: '05', title: 'M1 / M2 / M3', desc: 'Optuna TPE + Early Stop', status: 'Configurable' },
                { num: '06', title: 'Validación & Test', desc: 'Matrices, PR/ROC, F1', status: 'Auditado' },
                { num: '07', title: 'Comparación & Exp', desc: 'PDF, Word, Excel (SHA-256)', status: 'Exportable' },
              ].map((step, idx, arr) => (
                <React.Fragment key={step.num}>
                  <div style={{
                    minWidth: '135px',
                    padding: '14px 12px',
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    textAlign: 'center',
                    position: 'relative',
                  }}>
                    <span style={{ position: 'absolute', top: '6px', left: '8px', fontSize: '9px', fontFamily: 'var(--font-mono)', color: 'var(--color-primary)' }}>
                      {step.num}
                    </span>
                    <strong style={{ display: 'block', fontSize: '12px', marginTop: '6px', color: 'var(--text-main)' }}>{step.title}</strong>
                    <span style={{ display: 'block', fontSize: '10px', color: 'var(--text-dim)', margin: '4px 0 8px' }}>{step.desc}</span>
                    <span className="badge success" style={{ fontSize: '9px' }}>{step.status}</span>
                  </div>
                  {idx < arr.length - 1 && <span style={{ color: 'var(--color-primary)', fontSize: '16px' }}>➔</span>}
                </React.Fragment>
              ))}
            </div>
          </div>

          <div className="grid-cols-3">
            <div className="card" style={{ borderTop: '3px solid #0284c7' }}>
              <h4 style={{ color: '#0284c7', fontSize: '15px', marginBottom: '8px' }}>M1: Random Forest Classifier</h4>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Modelo supervisado multiclase. Sirve de baseline sólido e interpretable para la probabilidad de remediación de hallazgos. Inmune al sobreajuste por profundidad y robusto a valores atípicos.
              </p>
              <div style={{ marginTop: '12px', fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                Parada: Término de árboles o presupuesto Optuna.
              </div>
            </div>

            <div className="card" style={{ borderTop: '3px solid #10b981' }}>
              <h4 style={{ color: '#10b981', fontSize: '15px', marginBottom: '8px' }}>M2: XGBoost Classifier</h4>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Gradient Boosting con regularización L2. Maximiza la separación de riesgos críticos mediante calibración de probabilidades. Soporta parada temprana tras 30 rondas sin mejora en validación.
              </p>
              <div style={{ marginTop: '12px', fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                Parada: Early stopping (30 rondas) o límite máx.
              </div>
            </div>

            <div className="card" style={{ borderTop: '3px solid #f59e0b' }}>
              <h4 style={{ color: '#f59e0b', fontSize: '15px', marginBottom: '8px' }}>M3: Isolation Forest</h4>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                Detección no supervisada de anomalías. Identifica combinaciones atípicas de roles, antigüedad y privilegios sin depender de etiquetas preexistentes. Genera ranking priorizado para auditoría humana.
              </p>
              <div style={{ marginTop: '12px', fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
                Parada: Árboles de aislamiento completados.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 2. EXPLORACIÓN DE DATOS (EDA) */}
      {activeTab === 'eda' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {loadingEda && <p style={{ color: 'var(--color-primary)' }}>Ejecutando diagnóstico EDA en tiempo real...</p>}
          {edaData && (
            <>
              <div className="grid-cols-4">
                <div className="kpi-card-premium" style={{ '--card-accent': '#22D3EE' } as React.CSSProperties}>
                  <div className="kpi-card-top"><span className="kpi-card-label">Total Cuentas Evaluadas</span></div>
                  <div className="kpi-card-value">{edaData.total_records}</div>
                  <div className="kpi-card-subtext"><span>Hash SHA-256</span><code>{edaData.dataset_hash?.slice(0, 10)}...</code></div>
                </div>

                <div className="kpi-card-premium" style={{ '--card-accent': '#F59E0B' } as React.CSSProperties}>
                  <div className="kpi-card-top"><span className="kpi-card-label">Sin Logon Registrado</span></div>
                  <div className="kpi-card-value">{edaData.active_directory_telemetry?.accounts_without_logon ?? 0}</div>
                  <div className="kpi-card-subtext"><span>Proporción</span><span>{edaData.active_directory_telemetry?.accounts_without_logon_pct}%</span></div>
                </div>

                <div className="kpi-card-premium" style={{ '--card-accent': '#F43F5E' } as React.CSSProperties}>
                  <div className="kpi-card-top"><span className="kpi-card-label">Inactivas ≥ 90 Días</span></div>
                  <div className="kpi-card-value">{edaData.active_directory_telemetry?.accounts_inactive_90_days_or_more ?? 0}</div>
                  <div className="kpi-card-subtext"><span>Regla R01</span><span>Huérfanas potenciales</span></div>
                </div>

                <div className="kpi-card-premium" style={{ '--card-accent': '#818CF8' } as React.CSSProperties}>
                  <div className="kpi-card-top"><span className="kpi-card-label">Ratio Desbalance</span></div>
                  <div className="kpi-card-value">{edaData.target_class_distribution?.imbalance_ratio ?? 1}:1</div>
                  <div className="kpi-card-subtext"><span>Clase minoritaria</span><span>{edaData.target_class_distribution?.minority_class_count} cuentas</span></div>
                </div>
              </div>

              {/* Advertencia Técnica de AD */}
              <div className="card" style={{ borderLeft: '4px solid #F59E0B', background: 'rgba(245,158,11,0.08)' }}>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                  <AlertTriangle size={20} color="#F59E0B" style={{ flexShrink: 0, marginTop: '2px' }} />
                  <div>
                    <h4 style={{ color: '#F59E0B', fontSize: '14px', margin: '0 0 4px' }}>
                      Advertencia de Auditoría Active Directory: Replicación de lastLogon
                    </h4>
                    <p style={{ fontSize: '13px', color: 'var(--text-main)', margin: 0, lineHeight: 1.6 }}>
                      {edaData.active_directory_telemetry?.ad_technical_warning}
                    </p>
                  </div>
                </div>
              </div>

              <div className="grid-cols-2">
                {/* Desglose de Clases */}
                <div className="card">
                  <span className="card-title">Distribución de Clases de Severidad</span>
                  <table className="data-table" style={{ marginTop: '12px' }}>
                    <thead>
                      <tr>
                        <th>Severidad</th>
                        <th>Cuentas</th>
                        <th>Porcentaje</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(edaData.target_class_distribution?.classes ?? {}).map(([cls, info]) => (
                        <tr key={cls}>
                          <td><strong>{cls}</strong></td>
                          <td>{info.count}</td>
                          <td>{info.percentage}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Flags de Seguridad */}
                <div className="card">
                  <span className="card-title">Flags de Seguridad en Directorio</span>
                  <table className="data-table" style={{ marginTop: '12px' }}>
                    <thead>
                      <tr>
                        <th>Atributo Evaluado</th>
                        <th>Verdadero</th>
                        <th>Porcentaje</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(edaData.categorical_distributions?.security_flags ?? {}).map(([flag, info]) => (
                        <tr key={flag}>
                          <td><code>{flag}</code></td>
                          <td>{info.true_count}</td>
                          <td>{info.true_pct}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Recomendaciones EDA */}
              <div className="card">
                <span className="card-title" style={{ color: 'var(--color-primary)' }}>Recomendaciones del Diagnóstico EDA</span>
                <ul style={{ paddingLeft: '20px', marginTop: '10px', fontSize: '13px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {edaData.recommendations?.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </div>
      )}

      {/* 3. PREPROCESAMIENTO & PARTICIÓN 70/15/15 */}
      {activeTab === 'preprocessing' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="card">
            <h3 className="card-title" style={{ color: 'var(--color-primary)' }}>Partición Estratificada Antifuga (70 / 15 / 15)</h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '4px 0 16px' }}>
              Se garantiza aislamiento estricto entre conjuntos: el preprocesador ajusta imputadores de mediana y escaladores únicamente sobre Train (70%).
            </p>

            <div className="grid-cols-3">
              <div className="kpi-card-premium" style={{ '--card-accent': '#0284c7' } as React.CSSProperties}>
                <div className="kpi-card-top"><span className="kpi-card-label">Train (Entrenamiento)</span></div>
                <div className="kpi-card-value">70 %</div>
                <div className="kpi-card-subtext"><span>Ajuste de modelos</span><span>Imputer fit</span></div>
              </div>
              <div className="kpi-card-premium" style={{ '--card-accent': '#10b981' } as React.CSSProperties}>
                <div className="kpi-card-top"><span className="kpi-card-label">Validation (Interno)</span></div>
                <div className="kpi-card-value">15 %</div>
                <div className="kpi-card-subtext"><span>Optuna TPE Tuning</span><span>Early Stopping M2</span></div>
              </div>
              <div className="kpi-card-premium" style={{ '--card-accent': '#f59e0b' } as React.CSSProperties}>
                <div className="kpi-card-top"><span className="kpi-card-label">Test (Prueba Ciega)</span></div>
                <div className="kpi-card-value">15 %</div>
                <div className="kpi-card-subtext"><span>Evaluación final</span><span>Blind Test</span></div>
              </div>
            </div>
          </div>

          <div className="grid-cols-2">
            <div className="card">
              <h4 style={{ color: '#10b981', fontSize: '14px', marginBottom: '8px' }}>Variables Permitidas en la Matriz</h4>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {['active', 'is_admin', 'justification_verified', 'is_duplicate', 'password_never_expires', 'is_service', 'activity_days', 'review_days', 'role_count'].map((f) => (
                  <span key={f} className="badge success">✓ {f}</span>
                ))}
              </div>
            </div>

            <div className="card">
              <h4 style={{ color: '#F43F5E', fontSize: '14px', marginBottom: '8px' }}>Variables Excluidas por Seguridad y Causalidad</h4>
              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                {['username', 'external_id', 'email', 'domain', 'risk_score', 'severity', 'rule_R01..R06'].map((f) => (
                  <span key={f} className="badge critical">✕ {f}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. CONFIGURACIÓN DE MODELOS M1/M2/M3 */}
      {activeTab === 'configuration' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="grid-cols-3">
            {/* Tarjeta M1 */}
            <div className="card" style={{ borderTop: '3px solid #0284c7' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h4 style={{ color: '#0284c7', fontSize: '16px', margin: 0 }}>M1: Random Forest</h4>
                <input type="checkbox" checked={runM1} onChange={(e) => setRunM1(e.target.checked)} />
              </div>
              <p style={{ fontSize: '11px', color: 'var(--text-dim)', margin: '6px 0 14px' }}>Supervisado · Baseline · Pesos balanceados</p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>n_estimators (árboles):</label>
                  <input
                    type="number"
                    className="search-input"
                    value={m1Estimators}
                    onChange={(e) => setM1Estimators(parseInt(e.target.value) || 300)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>max_depth:</label>
                  <input
                    type="number"
                    className="search-input"
                    value={m1MaxDepth}
                    onChange={(e) => setM1MaxDepth(parseInt(e.target.value) || 12)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>min_samples_leaf:</label>
                  <input
                    type="number"
                    className="search-input"
                    value={m1MinLeaf}
                    onChange={(e) => setM1MinLeaf(parseInt(e.target.value) || 2)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Trials Optuna:</label>
                  <input
                    type="number"
                    className="search-input"
                    value={optunaTrialsM1}
                    onChange={(e) => setOptunaTrialsM1(parseInt(e.target.value) || 10)}
                  />
                </div>
              </div>
              <div style={{ marginTop: '14px', padding: '8px', background: 'rgba(2,132,199,0.1)', borderRadius: '4px', fontSize: '11px', color: '#38bdf8' }}>
                <strong>Parada:</strong> Construcción de árboles o presupuesto de tiempo/trials.
              </div>
            </div>

            {/* Tarjeta M2 */}
            <div className="card" style={{ borderTop: '3px solid #10b981' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h4 style={{ color: '#10b981', fontSize: '16px', margin: 0 }}>M2: XGBoost</h4>
                <input type="checkbox" checked={runM2} onChange={(e) => setRunM2(e.target.checked)} />
              </div>
              <p style={{ fontSize: '11px', color: 'var(--text-dim)', margin: '6px 0 14px' }}>Supervisado · Boosting optimizado · Early Stop</p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>n_estimators:</label>
                  <input
                    type="number"
                    className="search-input"
                    value={m2Estimators}
                    onChange={(e) => setM2Estimators(parseInt(e.target.value) || 300)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>learning_rate:</label>
                  <input
                    type="number"
                    step="0.01"
                    className="search-input"
                    value={m2LearningRate}
                    onChange={(e) => setM2LearningRate(parseFloat(e.target.value) || 0.05)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>max_depth:</label>
                  <input
                    type="number"
                    className="search-input"
                    value={m2MaxDepth}
                    onChange={(e) => setM2MaxDepth(parseInt(e.target.value) || 5)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Early Stopping Rounds:</label>
                  <input
                    type="number"
                    className="search-input"
                    value={m2EarlyStopping}
                    onChange={(e) => setM2EarlyStopping(parseInt(e.target.value) || 30)}
                  />
                </div>
              </div>
              <div style={{ marginTop: '14px', padding: '8px', background: 'rgba(16,185,129,0.1)', borderRadius: '4px', fontSize: '11px', color: '#6ee7b7' }}>
                <strong>Parada:</strong> 30 rondas sin mejora en validación o tope máximo.
              </div>
            </div>

            {/* Tarjeta M3 */}
            <div className="card" style={{ borderTop: '3px solid #f59e0b' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h4 style={{ color: '#f59e0b', fontSize: '16px', margin: 0 }}>M3: Isolation Forest</h4>
                <input type="checkbox" checked={runM3} onChange={(e) => setRunM3(e.target.checked)} />
              </div>
              <p style={{ fontSize: '11px', color: 'var(--text-dim)', margin: '6px 0 14px' }}>No Supervisado · Detección de Anomalías AD</p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>n_estimators:</label>
                  <input
                    type="number"
                    className="search-input"
                    value={m3Estimators}
                    onChange={(e) => setM3Estimators(parseInt(e.target.value) || 300)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>contamination:</label>
                  <select
                    className="select-filter"
                    value={m3Contamination}
                    onChange={(e) => setM3Contamination(e.target.value)}
                    style={{ width: '100%' }}
                  >
                    <option value="auto">auto (estimación estadística)</option>
                    <option value="0.05">0.05 (5% de anomalías)</option>
                    <option value="0.10">0.10 (10% de anomalías)</option>
                    <option value="0.15">0.15 (15% de anomalías)</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Semilla (Seed):</label>
                  <input
                    type="number"
                    className="search-input"
                    value={seed}
                    onChange={(e) => setSeed(parseInt(e.target.value) || 42)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Trials Optuna (M3):</label>
                  <input
                    type="number"
                    className="search-input"
                    value={optunaTrialsM3}
                    onChange={(e) => setOptunaTrialsM3(parseInt(e.target.value) || 8)}
                  />
                </div>
              </div>
              <div style={{ marginTop: '14px', padding: '8px', background: 'rgba(245,158,11,0.1)', borderRadius: '4px', fontSize: '11px', color: '#fcd34d' }}>
                <strong>Parada:</strong> Finalización de árboles de aislamiento en población.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. CONSOLA DE EJECUCIÓN & OPTUNA EN VIVO */}
      {activeTab === 'execution' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div>
                <h3 className="card-title">Consola de Entrenamiento en Tiempo Real</h3>
                <span style={{ fontSize: '12px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                  ID: {selectedJob?.job_id ?? 'Ninguno'} · Estado: <strong style={{ color: selectedJob?.status === 'completed' ? '#10b981' : 'var(--color-primary)' }}>{selectedJob?.status?.toUpperCase()}</strong>
                </span>
              </div>
              {isExecuting && (
                <button className="btn btn-danger btn-sm" onClick={handleCancel}>
                  <Square size={14} /> Cancelar Corrida
                </button>
              )}
            </div>

            {/* Barra de Progreso */}
            <div style={{ width: '100%', height: '10px', background: 'var(--bg-elevated)', borderRadius: '5px', overflow: 'hidden' }}>
              <div style={{
                width: `${selectedJob?.progress?.percent ?? (isExecuting ? 50 : 0)}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #0284c7, #10b981)',
                transition: 'width 0.3s ease'
              }} />
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginTop: '6px', color: 'var(--text-muted)' }}>
              <span>Fase actual: {selectedJob?.progress?.stage ?? 'espera'}</span>
              <strong style={{ color: 'var(--color-primary)' }}>{selectedJob?.progress?.percent ?? 0} %</strong>
            </div>
            <p style={{ marginTop: '10px', fontSize: '13px', color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
              {selectedJob?.progress?.message || 'Esperando inicio de experimento...'}
            </p>
          </div>

          {/* Registro de Trials Optuna */}
          {selectedJob?.result?.optuna_studies && (
            <div className="grid-cols-2">
              {Object.entries(selectedJob.result.optuna_studies).map(([modName, study]) => (
                <div key={modName} className="card">
                  <div className="card-header">
                    <span className="card-title" style={{ color: '#10b981' }}>Optuna Study: {modName}</span>
                    <span className="badge success">Mejor F1: {study.best_value}</span>
                  </div>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Trial #</th>
                        <th>F1 Validación</th>
                        <th>Hiperparámetros Evaluados</th>
                      </tr>
                    </thead>
                    <tbody>
                      {study.trials_history.slice(-5).map((t) => (
                        <tr key={t.trial}>
                          <td>#{t.trial}</td>
                          <td><strong style={{ color: '#10b981' }}>{t.score}</strong></td>
                          <td><code style={{ fontSize: '10px' }}>{JSON.stringify(t.params)}</code></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 6. MÉTRICAS & VALIDACIÓN */}
      {activeTab === 'evaluation' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {!selectedJob?.result ? (
            <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
              <p style={{ color: 'var(--text-muted)' }}>Ejecuta un entrenamiento para visualizar las métricas y matrices de confusión.</p>
            </div>
          ) : (
            <>
              <div className="grid-cols-2">
                {/* M1 Metrics */}
                {selectedJob.result.models.M1_RandomForest && (
                  <div className="card" style={{ borderTop: '3px solid #0284c7' }}>
                    <div className="card-header">
                      <span className="card-title" style={{ color: '#0284c7' }}>M1 (Random Forest) — Prueba Ciega (15%)</span>
                    </div>
                    <div className="grid-cols-3" style={{ marginBottom: '14px' }}>
                      <div className="kpi-card-premium" style={{ minHeight: '80px', padding: '12px' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Accuracy</span>
                        <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)' }}>
                          {selectedJob.result.models.M1_RandomForest.test_metrics.accuracy}
                        </div>
                      </div>
                      <div className="kpi-card-premium" style={{ minHeight: '80px', padding: '12px' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>F1-Macro</span>
                        <div style={{ fontSize: '20px', fontWeight: 700, color: '#0284c7' }}>
                          {selectedJob.result.models.M1_RandomForest.test_metrics.f1_macro}
                        </div>
                      </div>
                      <div className="kpi-card-premium" style={{ minHeight: '80px', padding: '12px' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Precision Macro</span>
                        <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)' }}>
                          {selectedJob.result.models.M1_RandomForest.test_metrics.precision_macro}
                        </div>
                      </div>
                    </div>

                    <h5 style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>Matriz de Confusión:</h5>
                    <div style={{ display: 'inline-flex', flexDirection: 'column', gap: '4px', padding: '8px', background: 'var(--bg-elevated)', borderRadius: '6px' }}>
                      {selectedJob.result.models.M1_RandomForest.test_metrics.confusion_matrix.map((row, rIdx) => (
                        <div key={rIdx} style={{ display: 'flex', gap: '4px' }}>
                          {row.map((val, cIdx) => (
                            <span key={cIdx} style={{
                              width: '38px',
                              height: '32px',
                              display: 'grid',
                              placeItems: 'center',
                              borderRadius: '4px',
                              fontWeight: 600,
                              fontSize: '12px',
                              background: rIdx === cIdx ? 'rgba(2,132,199,0.35)' : 'rgba(38,52,75,0.4)',
                              color: '#fff'
                            }}>
                              {val}
                            </span>
                          ))}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* M2 Metrics */}
                {selectedJob.result.models.M2_XGBoost && (
                  <div className="card" style={{ borderTop: '3px solid #10b981' }}>
                    <div className="card-header">
                      <span className="card-title" style={{ color: '#10b981' }}>M2 (XGBoost) — Prueba Ciega (15%)</span>
                    </div>
                    <div className="grid-cols-3" style={{ marginBottom: '14px' }}>
                      <div className="kpi-card-premium" style={{ minHeight: '80px', padding: '12px' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Accuracy</span>
                        <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)' }}>
                          {selectedJob.result.models.M2_XGBoost.test_metrics.accuracy}
                        </div>
                      </div>
                      <div className="kpi-card-premium" style={{ minHeight: '80px', padding: '12px' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>F1-Macro</span>
                        <div style={{ fontSize: '20px', fontWeight: 700, color: '#10b981' }}>
                          {selectedJob.result.models.M2_XGBoost.test_metrics.f1_macro}
                        </div>
                      </div>
                      <div className="kpi-card-premium" style={{ minHeight: '80px', padding: '12px' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Precision Macro</span>
                        <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-main)' }}>
                          {selectedJob.result.models.M2_XGBoost.test_metrics.precision_macro}
                        </div>
                      </div>
                    </div>

                    <h5 style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '8px' }}>Matriz de Confusión:</h5>
                    <div style={{ display: 'inline-flex', flexDirection: 'column', gap: '4px', padding: '8px', background: 'var(--bg-elevated)', borderRadius: '6px' }}>
                      {selectedJob.result.models.M2_XGBoost.test_metrics.confusion_matrix.map((row, rIdx) => (
                        <div key={rIdx} style={{ display: 'flex', gap: '4px' }}>
                          {row.map((val, cIdx) => (
                            <span key={cIdx} style={{
                              width: '38px',
                              height: '32px',
                              display: 'grid',
                              placeItems: 'center',
                              borderRadius: '4px',
                              fontWeight: 600,
                              fontSize: '12px',
                              background: rIdx === cIdx ? 'rgba(16,185,129,0.35)' : 'rgba(38,52,75,0.4)',
                              color: '#fff'
                            }}>
                              {val}
                            </span>
                          ))}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Gráficos Incrustados en Base64 */}
              {selectedJob.result.charts && (
                <div className="grid-cols-2">
                  {Object.entries(selectedJob.result.charts).map(([cName, b64]) => (
                    <div key={cName} className="card" style={{ textAlign: 'center' }}>
                      <span className="card-title" style={{ display: 'block', marginBottom: '10px' }}>
                        {cName.replace(/_/g, ' ').toUpperCase()}
                      </span>
                      <img
                        src={`data:image/png;base64,${b64}`}
                        alt={cName}
                        style={{ maxWidth: '100%', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}
                      />
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* 7. COMPARACIÓN DE MODELOS */}
      {activeTab === 'comparison' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="card">
            <h3 className="card-title" style={{ color: 'var(--color-primary)' }}>
              Matriz Comparativa de Modelos Supervisados (M1 vs M2)
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '4px 0 16px' }}>
              Evaluación rigurosa sobre el 15% de prueba ciego. Ambos modelos compiten bajo el mismo objetivo supervisado.
            </p>

            {selectedJob?.result?.comparison_table ? (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Métrica de Rendimiento</th>
                    <th>M1: Random Forest</th>
                    <th>M2: XGBoost</th>
                    <th>Modelo Superior</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedJob.result.comparison_table.map((row) => (
                    <tr key={row.metric}>
                      <td><strong>{row.metric}</strong></td>
                      <td>{row.m1_random_forest ?? '-'}</td>
                      <td>{row.m2_xgboost ?? '-'}</td>
                      <td>
                        <span className="badge" style={{
                          background: row.best_model.includes('M1') ? 'rgba(2,132,199,0.2)' : 'rgba(16,185,129,0.2)',
                          color: row.best_model.includes('M1') ? '#0284c7' : '#10b981',
                        }}>
                          {row.best_model}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ color: 'var(--text-muted)' }}>No hay experimentos completados para comparar.</p>
            )}
          </div>

          {/* Panel M3: Isolation Forest */}
          {selectedJob?.result?.models.M3_IsolationForest && (
            <div className="card" style={{ borderTop: '3px solid #f59e0b' }}>
              <div className="card-header">
                <span className="card-title" style={{ color: '#f59e0b' }}>
                  M3: Detección No Supervisada de Anomalías (Isolation Forest)
                </span>
                <span className="badge high">
                  {selectedJob.result.models.M3_IsolationForest.anomaly_rate_pct}% Cuentas Anómalas
                </span>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                {selectedJob.result.models.M3_IsolationForest.methodological_note}
              </p>

              <h5 style={{ fontSize: '12px', color: 'var(--text-main)', marginTop: '14px', marginBottom: '8px' }}>
                Top Identidades con Mayor Desviación Anómala:
              </h5>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Username</th>
                    <th>Dominio AD</th>
                    <th>Puntaje Anomalía</th>
                    <th>Score R01–R06</th>
                    <th>Admin</th>
                    <th>Pwd Never Expires</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedJob.result.models.M3_IsolationForest.top_anomalies.map((anom) => (
                    <tr key={anom.rank}>
                      <td>#{anom.rank}</td>
                      <td><code>{anom.username}</code></td>
                      <td>{anom.source}</td>
                      <td><strong style={{ color: '#f59e0b' }}>{anom.anomaly_score}</strong></td>
                      <td>{anom.deterministic_risk_score}</td>
                      <td>{anom.is_admin ? '🛡️ Sí' : 'No'}</td>
                      <td>{anom.password_never_expires ? '⚠️ Sí' : 'No'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* 8. REPORTES & TRAZABILIDAD */}
      {activeTab === 'reports' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="card">
            <h3 className="card-title" style={{ color: 'var(--color-primary)' }}>
              Exportación Formal de Reportes de Entrenamiento IA
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--text-muted)', margin: '4px 0 16px' }}>
              Descarga directa de informes de auditoría con firma criptográfica SHA-256 del dataset, parámetros de hiperoptimización Optuna y curvas.
            </p>

            {selectedJob?.job_id ? (
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <a
                  href={getTrainingReportDownloadUrl(selectedJob.job_id, 'pdf')}
                  target="_blank"
                  rel="noreferrer"
                  className="btn"
                  style={{ background: '#ef4444', color: '#fff' }}
                >
                  <Download size={14} /> Descargar Reporte PDF
                </a>
                <a
                  href={getTrainingReportDownloadUrl(selectedJob.job_id, 'docx')}
                  target="_blank"
                  rel="noreferrer"
                  className="btn"
                  style={{ background: '#2563eb', color: '#fff' }}
                >
                  <Download size={14} /> Descargar Reporte Word (.docx)
                </a>
                <a
                  href={getTrainingReportDownloadUrl(selectedJob.job_id, 'xlsx')}
                  target="_blank"
                  rel="noreferrer"
                  className="btn"
                  style={{ background: '#10b981', color: '#fff' }}
                >
                  <Download size={14} /> Descargar Reporte Excel (.xlsx)
                </a>
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)' }}>Selecciona un experimento para habilitar las descargas.</p>
            )}
          </div>

          {/* Historial de Experimentos */}
          <div className="card">
            <span className="card-title" style={{ marginBottom: '12px', display: 'block' }}>
              Historial de Experimentos Registrados
            </span>
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID Experimento</th>
                  <th>Estado</th>
                  <th>Actor / Auditor</th>
                  <th>Fecha de Registro</th>
                  <th>Acción</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.job_id}>
                    <td><code>{j.job_id}</code></td>
                    <td>
                      <span className={`badge ${j.status === 'completed' ? 'success' : j.status === 'running' ? 'medium' : 'critical'}`}>
                        {j.status}
                      </span>
                    </td>
                    <td>{j.actor}</td>
                    <td>{j.created_at ? new Date(j.created_at).toLocaleString('es-PE') : '-'}</td>
                    <td>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={async () => {
                          const full = await getTrainingJobDetail(j.job_id)
                          setSelectedJob(full)
                          setActiveTab('evaluation')
                        }}
                      >
                        Ver Métricas
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
