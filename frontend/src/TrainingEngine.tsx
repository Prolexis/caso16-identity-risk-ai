import React, { useState, useEffect, useCallback } from 'react'
import {
  EdaResponse,
  TrainingDefaults,
  TrainingJob,
  getEda,
  getTrainingDefaults,
  getTrainingJobs,
  getTrainingJob,
  startTraining,
  cancelTrainingJob,
  getReportDownloadUrl,
} from './api'

type TabType =
  | 'methodology'
  | 'eda'
  | 'preprocessing'
  | 'configuration'
  | 'monitor'
  | 'metrics'
  | 'comparison'
  | 'reports'

export const TrainingEngine: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('methodology')
  const [useDemoDataset, setUseDemoDataset] = useState(false)
  const [edaData, setEdaData] = useState<EdaResponse | null>(null)
  const [edaLoading, setEdaLoading] = useState(false)

  const [defaults, setDefaults] = useState<TrainingDefaults | null>(null)
  const [jobs, setJobs] = useState<TrainingJob[]>([])
  const [selectedJob, setSelectedJob] = useState<TrainingJob | null>(null)
  const [isTraining, setIsTraining] = useState(false)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  // Configuración de modelos
  const [runM1, setRunM1] = useState(true)
  const [runM2, setRunM2] = useState(true)
  const [runM3, setRunM3] = useState(true)
  const [useOptuna, setUseOptuna] = useState(true)
  const [optunaTrialsM1, setOptunaTrialsM1] = useState(10)
  const [optunaTrialsM2, setOptunaTrialsM2] = useState(10)
  const [optunaTrialsM3, setOptunaTrialsM3] = useState(8)
  const [seed, setSeed] = useState(42)

  // Hiperparámetros M1
  const [m1Estimators, setM1Estimators] = useState(300)
  const [m1MaxDepth, setM1MaxDepth] = useState(12)
  const [m1MinLeaf, setM1MinLeaf] = useState(2)

  // Hiperparámetros M2
  const [m2Estimators, setM2Estimators] = useState(300)
  const [m2MaxDepth, setM2MaxDepth] = useState(5)
  const [m2LearningRate, setM2LearningRate] = useState(0.05)
  const [m2EarlyStopping, setM2EarlyStopping] = useState(30)

  // Hiperparámetros M3
  const [m3Estimators, setM3Estimators] = useState(300)
  const [m3Contamination, setM3Contamination] = useState('auto')

  // Carga inicial
  const loadEda = useCallback(async (demo: boolean) => {
    setEdaLoading(true)
    try {
      const data = await getEda(demo)
      setEdaData(data)
    } catch (err) {
      console.error('Error cargando EDA:', err)
    } finally {
      setEdaLoading(false)
    }
  }, [])

  const loadDefaultsAndJobs = useCallback(async () => {
    try {
      const [defs, jobsRes] = await Promise.all([getTrainingDefaults(), getTrainingJobs()])
      setDefaults(defs)
      setJobs(jobsRes.jobs)
      if (jobsRes.jobs.length > 0) {
        const latest = jobsRes.jobs[0]
        const fullJob = await getTrainingJob(latest.job_id)
        setSelectedJob(fullJob)
      }
    } catch (err) {
      console.error('Error cargando defaults/jobs:', err)
    }
  }, [])

  useEffect(() => {
    void loadEda(useDemoDataset)
    void loadDefaultsAndJobs()
  }, [loadEda, loadDefaultsAndJobs, useDemoDataset])

  // Polling de job en ejecución
  useEffect(() => {
    if (!isTraining && (!selectedJob || selectedJob.status !== 'running')) return
    const interval = setInterval(async () => {
      if (!selectedJob) return
      try {
        const updated = await getTrainingJob(selectedJob.job_id)
        setSelectedJob(updated)
        if (updated.status === 'completed' || updated.status === 'failed' || updated.status === 'cancelled') {
          setIsTraining(false)
          // refrescar lista
          const jobsRes = await getTrainingJobs()
          setJobs(jobsRes.jobs)
        }
      } catch (err) {
        console.error('Error polling job:', err)
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [isTraining, selectedJob])

  const handleStartTraining = async () => {
    setActionMessage('Iniciando entrenamiento y optimización...')
    setIsTraining(true)
    try {
      const res = await startTraining({
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
        },
        params_m2: {
          n_estimators: m2Estimators,
          max_depth: m2MaxDepth,
          learning_rate: m2LearningRate,
          early_stopping_rounds: m2EarlyStopping,
        },
        params_m3: {
          n_estimators: m3Estimators,
          contamination: m3Contamination === 'auto' ? 'auto' : parseFloat(m3Contamination),
        },
      })
      setActionMessage(`Trabajo iniciado con ID: ${res.job_id}`)
      setActiveTab('monitor')
      const newJob = await getTrainingJob(res.job_id)
      setSelectedJob(newJob)
      const list = await getTrainingJobs()
      setJobs(list.jobs)
    } catch (err: unknown) {
      setIsTraining(false)
      setActionMessage(`Error al iniciar: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  const handleCancelTraining = async () => {
    if (!selectedJob) return
    try {
      await cancelTrainingJob(selectedJob.job_id)
      setActionMessage('Señal de parada enviada.')
    } catch (err: unknown) {
      setActionMessage(`Error cancelando: ${err instanceof Error ? err.message : String(err)}`)
    }
  }

  return (
    <div className="training-engine-shell">
      {/* Barra superior de controles del motor */}
      <div className="te-header-row">
        <div>
          <span className="eyebrow">MÓDULO DE APRENDIZAJE AUTOMÁTICO</span>
          <h2 style={{ margin: '4px 0 6px', fontSize: '26px' }}>Motor de Entrenamiento de IA</h2>
          <p style={{ color: '#8fa4bc', fontSize: '13px', margin: 0 }}>
            Metodología EDA → Preprocesamiento → Partición 70/15/15 → M1/M2/M3 & Optuna → Validación Ciega → Reportes.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <label className="te-toggle-label">
            <input
              type="checkbox"
              checked={useDemoDataset}
              onChange={(e) => setUseDemoDataset(e.target.checked)}
            />
            <span>{useDemoDataset ? 'Dataset Sintético (Controlado)' : 'Dataset Telemetría AD Real'}</span>
          </label>
          <button
            className="refresh-button"
            style={{ background: '#10b981', color: '#07111f' }}
            onClick={handleStartTraining}
            disabled={isTraining}
          >
            {isTraining ? 'Entrenando...' : '▶ Iniciar Entrenamiento'}
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="te-action-bar">
          <span>ℹ {actionMessage}</span>
          <button onClick={() => setActionMessage(null)}>✕</button>
        </div>
      )}

      {/* Navegación por pestañas */}
      <nav className="te-nav-tabs">
        <button className={activeTab === 'methodology' ? 'active' : ''} onClick={() => setActiveTab('methodology')}>
          1. Metodología
        </button>
        <button className={activeTab === 'eda' ? 'active' : ''} onClick={() => setActiveTab('eda')}>
          2. EDA & Calidad
        </button>
        <button className={activeTab === 'preprocessing' ? 'active' : ''} onClick={() => setActiveTab('preprocessing')}>
          3. Preproceso & Partición
        </button>
        <button className={activeTab === 'configuration' ? 'active' : ''} onClick={() => setActiveTab('configuration')}>
          4. Configuración M1/M2/M3
        </button>
        <button className={activeTab === 'monitor' ? 'active' : ''} onClick={() => setActiveTab('monitor')}>
          5. Monitor & Optuna
        </button>
        <button className={activeTab === 'metrics' ? 'active' : ''} onClick={() => setActiveTab('metrics')}>
          6. Métricas & Gráficos
        </button>
        <button className={activeTab === 'comparison' ? 'active' : ''} onClick={() => setActiveTab('comparison')}>
          7. Comparación de Modelos
        </button>
        <button className={activeTab === 'reports' ? 'active' : ''} onClick={() => setActiveTab('reports')}>
          8. Reportes & Trazabilidad
        </button>
      </nav>

      {/* Contenido de cada pestaña */}
      <div className="te-tab-body">
        {/* TAB 1: METODOLOGÍA */}
        {activeTab === 'methodology' && (
          <div className="te-tab-pane">
            <div className="te-card">
              <h3 style={{ margin: '0 0 14px', color: '#70e3e1' }}>Diagrama Metodológico del Proceso de Entrenamiento</h3>
              <p style={{ color: '#94a9bf', fontSize: '13px' }}>
                Cumplimiento estricto del ciclo de experimentación y auditoría de ciberseguridad. Cada fase aplica controles
                para evitar fuga de información hacia los conjuntos de validación y prueba.
              </p>
              <div className="te-methodology-flow">
                {[
                  { step: '01', title: 'Datos AD/LDAP', sub: 'Ingesta y esquema', icon: '📥', status: 'Listo' },
                  { step: '02', title: 'EDA & Calidad', sub: 'Nulos, outliers, AD timestamps', icon: '🔍', status: 'Activo' },
                  { step: '03', title: 'Preprocesamiento', sub: 'Imputación solo en Train', icon: '⚙️', status: 'Listo' },
                  { step: '04', title: 'Partición 70/15/15', sub: 'Prueba ciega reservada', icon: '✂️', status: 'Blind' },
                  { step: '05', title: 'M1 / M2 / M3', sub: 'Optuna TPE + Early Stop', icon: '🤖', status: 'Listo' },
                  { step: '06', title: 'Validación & Test', sub: 'Métricas y Ranking', icon: '📊', status: 'Listo' },
                  { step: '07', title: 'Reportes y Auditoría', sub: 'PDF, Word, Excel & Hash', icon: '📑', status: 'SHA-256' },
                ].map((item, idx, arr) => (
                  <React.Fragment key={item.step}>
                    <div className="te-flow-node">
                      <span className="te-node-step">{item.step}</span>
                      <div className="te-node-icon">{item.icon}</div>
                      <strong>{item.title}</strong>
                      <small>{item.sub}</small>
                      <span className="te-node-badge">{item.status}</span>
                    </div>
                    {idx < arr.length - 1 && <span className="te-flow-arrow">➔</span>}
                  </React.Fragment>
                ))}
              </div>
            </div>

            <div className="te-grid-2" style={{ marginTop: '16px' }}>
              <div className="te-card">
                <h4 style={{ color: '#61e9bc', margin: '0 0 10px' }}>Propuesta Técnica de Modelos</h4>
                <ul className="te-list">
                  <li>
                    <strong>M1 (Random Forest):</strong> Clasificador supervisado multiclase para estimar severidad y
                    remediación de hallazgos. Baseline robusto a no linealidades.
                  </li>
                  <li>
                    <strong>M2 (XGBoost):</strong> Clasificador supervisado con gradient boosting y regularización L2.
                    Incluye parada temprana (early stopping 30 rondas).
                  </li>
                  <li>
                    <strong>M3 (Isolation Forest):</strong> Detección no supervisada de identidades anómalas. Aísla
                    cuentas con privilegios o inactividad atípica sin depender de etiquetas preexistentes.
                  </li>
                </ul>
              </div>

              <div className="te-card">
                <h4 style={{ color: '#f6b65b', margin: '0 0 10px' }}>Controles Antifuga y Rigor Académico</h4>
                <ul className="te-list">
                  <li>
                    <strong>Partición Ciega:</strong> El 15% de prueba nunca se consulta durante la optimización con Optuna.
                  </li>
                  <li>
                    <strong>Imputación Segura:</strong> SimpleImputer ajusta la mediana exclusivamente en el conjunto de
                    entrenamiento (Train).
                  </li>
                  <li>
                    <strong>Separación de Tareas:</strong> M1 y M2 son comparables bajo el mismo objetivo supervisado;
                    M3 realiza una tarea no supervisada distinta y no se inventan métricas supervisadas para él.
                  </li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: EDA & CALIDAD */}
        {activeTab === 'eda' && (
          <div className="te-tab-pane">
            {edaLoading && <p style={{ color: '#70e3e1' }}>Ejecutando análisis exploratorio en tiempo real...</p>}
            {edaData && (
              <>
                <div className="te-grid-4">
                  <div className="te-metric-card">
                    <span>Total Cuentas Analizadas</span>
                    <strong>{edaData.total_records}</strong>
                    <small>Hash: {edaData.dataset_hash?.slice(0, 12)}...</small>
                  </div>
                  <div className="te-metric-card">
                    <span>Sin Registro de Logon</span>
                    <strong>{edaData.active_directory_telemetry?.accounts_without_logon ?? 0}</strong>
                    <small>{edaData.active_directory_telemetry?.accounts_without_logon_pct ?? 0}% del total</small>
                  </div>
                  <div className="te-metric-card">
                    <span>Inactivas ≥ 90 Días</span>
                    <strong>{edaData.active_directory_telemetry?.accounts_inactive_90_days_or_more ?? 0}</strong>
                    <small>Regla R01 potencial</small>
                  </div>
                  <div className="te-metric-card">
                    <span>Ratio de Desbalance</span>
                    <strong>{edaData.target_class_distribution?.imbalance_ratio ?? 1}:1</strong>
                    <small>Minoritaria: {edaData.target_class_distribution?.minority_class_count ?? 0} cuentas</small>
                  </div>
                </div>

                <div className="te-card" style={{ marginTop: '16px' }}>
                  <h4 style={{ color: '#f6b65b', margin: '0 0 8px' }}>⚠️ Advertencia Técnica de Active Directory (lastLogon)</h4>
                  <p style={{ fontSize: '13px', color: '#c0cedc', lineHeight: 1.6, margin: 0 }}>
                    {edaData.active_directory_telemetry?.ad_technical_warning}
                  </p>
                </div>

                <div className="te-grid-2" style={{ marginTop: '16px' }}>
                  <div className="te-card">
                    <h4 style={{ margin: '0 0 12px' }}>Distribución de Clases de Riesgo</h4>
                    <table className="te-table">
                      <thead>
                        <tr>
                          <th>Clase</th>
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

                  <div className="te-card">
                    <h4 style={{ margin: '0 0 12px' }}>Flags de Seguridad en Inventario</h4>
                    <table className="te-table">
                      <thead>
                        <tr>
                          <th>Atributo Evaluado</th>
                          <th>Activos (True)</th>
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

                <div className="te-card" style={{ marginTop: '16px' }}>
                  <h4 style={{ color: '#70e3e1', margin: '0 0 10px' }}>Recomendaciones del Diagnóstico EDA</h4>
                  <ul className="te-list">
                    {edaData.recommendations?.map((rec, i) => (
                      <li key={i}>{rec}</li>
                    ))}
                  </ul>
                </div>
              </>
            )}
          </div>
        )}

        {/* TAB 3: PREPROCESAMIENTO & PARTICIÓN */}
        {activeTab === 'preprocessing' && (
          <div className="te-tab-pane">
            <div className="te-card">
              <h3 style={{ margin: '0 0 12px', color: '#70e3e1' }}>Pipeline de Preprocesamiento y Partición 70 / 15 / 15</h3>
              <p style={{ color: '#94a9bf', fontSize: '13px' }}>
                Control estricto de fuga de datos. Los identificadores únicos (username, external_id, emails) se excluyen
                de la matriz de características.
              </p>

              <div className="te-grid-3" style={{ marginTop: '16px' }}>
                <div className="te-metric-card" style={{ borderLeft: '4px solid #0284c7' }}>
                  <span>Conjunto de Entrenamiento</span>
                  <strong>70 %</strong>
                  <small>Ajuste de imputador, escalado y modelos</small>
                </div>
                <div className="te-metric-card" style={{ borderLeft: '4px solid #10b981' }}>
                  <span>Conjunto de Validación</span>
                  <strong>15 %</strong>
                  <small>Evaluación de Optuna y Early Stopping M2</small>
                </div>
                <div className="te-metric-card" style={{ borderLeft: '4px solid #f59e0b' }}>
                  <span>Conjunto de Prueba Ciego</span>
                  <strong>15 %</strong>
                  <small>Evaluación final única (blind test)</small>
                </div>
              </div>

              <div style={{ marginTop: '20px' }}>
                <h4 style={{ color: '#c0cedc', margin: '0 0 10px' }}>Variables Permitidas en la Matriz de Características</h4>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {[
                    'active (bool)',
                    'is_admin (bool)',
                    'justification_verified (bool)',
                    'is_duplicate (bool)',
                    'password_never_expires (bool)',
                    'is_service (derivada)',
                    'activity_days (numérico)',
                    'review_days (numérico)',
                    'role_count (conteo)',
                  ].map((feat) => (
                    <span key={feat} className="te-pill">
                      ✓ {feat}
                    </span>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: '20px' }}>
                <h4 style={{ color: '#ef4444', margin: '0 0 10px' }}>Variables Excluidas por Seguridad y Fuga Causal</h4>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {['username', 'external_id', 'email', 'domain', 'risk_score', 'severity', 'rule_R01..R06'].map(
                    (feat) => (
                      <span key={feat} className="te-pill" style={{ borderColor: 'rgba(239,68,68,.3)', color: '#f87171' }}>
                        ✕ {feat}
                      </span>
                    )
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: CONFIGURACIÓN M1, M2, M3 */}
        {activeTab === 'configuration' && (
          <div className="te-tab-pane">
            <div className="te-grid-3">
              {/* Tarjeta M1 */}
              <div className="te-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ margin: 0, color: '#0284c7' }}>M1: Random Forest</h3>
                  <label>
                    <input type="checkbox" checked={runM1} onChange={(e) => setRunM1(e.target.checked)} />
                  </label>
                </div>
                <p style={{ color: '#8ea4ba', fontSize: '11px', margin: '8px 0 14px' }}>
                  Supervisado · Baseline no paramétrico · Pesos balanceados
                </p>

                <div className="te-form-group">
                  <label>n_estimators (árboles):</label>
                  <input
                    type="number"
                    value={m1Estimators}
                    onChange={(e) => setM1Estimators(parseInt(e.target.value) || 300)}
                  />
                </div>
                <div className="te-form-group">
                  <label>max_depth (profundidad):</label>
                  <input
                    type="number"
                    value={m1MaxDepth}
                    onChange={(e) => setM1MaxDepth(parseInt(e.target.value) || 12)}
                  />
                </div>
                <div className="te-form-group">
                  <label>min_samples_leaf:</label>
                  <input
                    type="number"
                    value={m1MinLeaf}
                    onChange={(e) => setM1MinLeaf(parseInt(e.target.value) || 2)}
                  />
                </div>
                <div className="te-form-group">
                  <label>Optuna Trials:</label>
                  <input
                    type="number"
                    value={optunaTrialsM1}
                    onChange={(e) => setOptunaTrialsM1(parseInt(e.target.value) || 10)}
                  />
                </div>
                <div className="te-cond-box">
                  <strong>Condición de Parada:</strong> Finalización de árboles especificados o límite de trials Optuna.
                </div>
              </div>

              {/* Tarjeta M2 */}
              <div className="te-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ margin: 0, color: '#10b981' }}>M2: XGBoost</h3>
                  <label>
                    <input type="checkbox" checked={runM2} onChange={(e) => setRunM2(e.target.checked)} />
                  </label>
                </div>
                <p style={{ color: '#8ea4ba', fontSize: '11px', margin: '8px 0 14px' }}>
                  Supervisado · Boosting optimizado · Fallback scikit-learn
                </p>

                <div className="te-form-group">
                  <label>n_estimators:</label>
                  <input
                    type="number"
                    value={m2Estimators}
                    onChange={(e) => setM2Estimators(parseInt(e.target.value) || 300)}
                  />
                </div>
                <div className="te-form-group">
                  <label>learning_rate:</label>
                  <input
                    type="number"
                    step="0.01"
                    value={m2LearningRate}
                    onChange={(e) => setM2LearningRate(parseFloat(e.target.value) || 0.05)}
                  />
                </div>
                <div className="te-form-group">
                  <label>max_depth:</label>
                  <input
                    type="number"
                    value={m2MaxDepth}
                    onChange={(e) => setM2MaxDepth(parseInt(e.target.value) || 5)}
                  />
                </div>
                <div className="te-form-group">
                  <label>Early Stopping Rounds:</label>
                  <input
                    type="number"
                    value={m2EarlyStopping}
                    onChange={(e) => setM2EarlyStopping(parseInt(e.target.value) || 30)}
                  />
                </div>
                <div className="te-cond-box">
                  <strong>Condición de Parada:</strong> 30 rondas sin mejora en validación o tope de estimadores.
                </div>
              </div>

              {/* Tarjeta M3 */}
              <div className="te-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h3 style={{ margin: 0, color: '#f59e0b' }}>M3: Isolation Forest</h3>
                  <label>
                    <input type="checkbox" checked={runM3} onChange={(e) => setRunM3(e.target.checked)} />
                  </label>
                </div>
                <p style={{ color: '#8ea4ba', fontSize: '11px', margin: '8px 0 14px' }}>
                  No Supervisado · Detección de Anomalías de Cuentas AD
                </p>

                <div className="te-form-group">
                  <label>n_estimators:</label>
                  <input
                    type="number"
                    value={m3Estimators}
                    onChange={(e) => setM3Estimators(parseInt(e.target.value) || 300)}
                  />
                </div>
                <div className="te-form-group">
                  <label>contamination:</label>
                  <select
                    value={m3Contamination}
                    onChange={(e) => setM3Contamination(e.target.value)}
                    style={{ background: '#0a1929', color: '#edf4ff', border: '1px solid #334155', borderRadius: '4px', padding: '6px' }}
                  >
                    <option value="auto">auto (estimación estadística)</option>
                    <option value="0.05">0.05 (5% anomalías)</option>
                    <option value="0.10">0.10 (10% anomalías)</option>
                    <option value="0.15">0.15 (15% anomalías)</option>
                  </select>
                </div>
                <div className="te-form-group">
                  <label>Optuna Trials (Opcional):</label>
                  <input
                    type="number"
                    value={optunaTrialsM3}
                    onChange={(e) => setOptunaTrialsM3(parseInt(e.target.value) || 8)}
                  />
                </div>
                <div className="te-form-group">
                  <label>Semilla (Seed):</label>
                  <input
                    type="number"
                    value={seed}
                    onChange={(e) => setSeed(parseInt(e.target.value) || 42)}
                  />
                </div>
                <div className="te-cond-box">
                  <strong>Condición de Parada:</strong> Finalización de árboles de aislamiento en población.
                </div>
              </div>
            </div>

            <div className="te-card" style={{ marginTop: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <strong style={{ color: '#70e3e1' }}>Optimización con Optuna (TPE Sampler)</strong>
                <p style={{ color: '#8ea4ba', fontSize: '12px', margin: '4px 0 0' }}>
                  Optimiza hiperparámetros de M1 y M2 evaluando exclusivamente la función objetivo en validación interna.
                </p>
              </div>
              <label className="te-toggle-label">
                <input type="checkbox" checked={useOptuna} onChange={(e) => setUseOptuna(e.target.checked)} />
                <span>{useOptuna ? 'Optuna Activado' : 'Valores Fijos'}</span>
              </label>
            </div>
          </div>
        )}

        {/* TAB 5: MONITOR & OPTUNA */}
        {activeTab === 'monitor' && (
          <div className="te-tab-pane">
            <div className="te-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <div>
                  <h3 style={{ margin: 0 }}>Monitor de Ejecución en Tiempo Real</h3>
                  <small style={{ color: '#8fa4bc' }}>
                    ID: {selectedJob?.job_id ?? 'Sin ejecución'} · Estado: <strong>{selectedJob?.status ?? 'Inactivo'}</strong>
                  </small>
                </div>
                {isTraining && (
                  <button className="te-btn-cancel" onClick={handleCancelTraining}>
                    ⏹ Cancelar Corrida
                  </button>
                )}
              </div>

              {/* Barra de progreso */}
              <div className="te-progress-bar-container">
                <div
                  className="te-progress-bar-fill"
                  style={{ width: `${selectedJob?.progress?.percent ?? (isTraining ? 40 : 0)}%` }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '6px', fontSize: '11px', color: '#8fa4bc' }}>
                <span>Fase: {selectedJob?.progress?.stage ?? 'espera'}</span>
                <span>{selectedJob?.progress?.percent ?? 0} %</span>
              </div>
              <p style={{ fontSize: '13px', color: '#70e3e1', marginTop: '10px' }}>
                {selectedJob?.progress?.message ?? 'Sin mensajes de progreso.'}
              </p>
            </div>

            {/* Estudios de Optuna */}
            {selectedJob?.result?.optuna_studies && (
              <div className="te-grid-2" style={{ marginTop: '16px' }}>
                {Object.entries(selectedJob.result.optuna_studies).map(([modName, study]) => (
                  <div key={modName} className="te-card">
                    <h4 style={{ margin: '0 0 8px', color: '#10b981' }}>Optuna: {modName}</h4>
                    <p style={{ fontSize: '12px', color: '#8fa4bc', margin: '0 0 10px' }}>
                      Mejor F1-Macro Validación: <strong>{study.best_value}</strong> ({study.trials_count} trials)
                    </p>
                    <table className="te-table">
                      <thead>
                        <tr>
                          <th>Trial #</th>
                          <th>Score F1</th>
                          <th>Hiperparámetros Clave</th>
                        </tr>
                      </thead>
                      <tbody>
                        {study.trials_history.slice(-6).map((t) => (
                          <tr key={t.trial}>
                            <td>#{t.trial}</td>
                            <td><strong>{t.score}</strong></td>
                            <td><code>{JSON.stringify(t.params)}</code></td>
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

        {/* TAB 6: MÉTRICAS & GRÁFICOS */}
        {activeTab === 'metrics' && (
          <div className="te-tab-pane">
            {!selectedJob?.result ? (
              <div className="te-card">
                <p style={{ color: '#8fa4bc', textAlign: 'center', margin: '20px 0' }}>
                  No hay resultados de entrenamiento disponibles. Inicia una corrida para visualizar métricas y gráficos.
                </p>
              </div>
            ) : (
              <>
                <div className="te-grid-2">
                  {/* M1 Metrics */}
                  {selectedJob.result.models.M1_RandomForest && (
                    <div className="te-card">
                      <h3 style={{ color: '#0284c7', margin: '0 0 10px' }}>M1 (Random Forest) — Prueba Ciega</h3>
                      <div className="te-grid-3" style={{ marginBottom: '14px' }}>
                        <div className="te-metric-card">
                          <span>Accuracy</span>
                          <strong>{selectedJob.result.models.M1_RandomForest.test_metrics.accuracy}</strong>
                        </div>
                        <div className="te-metric-card">
                          <span>F1-Macro</span>
                          <strong>{selectedJob.result.models.M1_RandomForest.test_metrics.f1_macro}</strong>
                        </div>
                        <div className="te-metric-card">
                          <span>Precision Macro</span>
                          <strong>{selectedJob.result.models.M1_RandomForest.test_metrics.precision_macro}</strong>
                        </div>
                      </div>

                      <h4 style={{ margin: '12px 0 6px', fontSize: '12px' }}>Matriz de Confusión:</h4>
                      <div className="te-cm-grid">
                        {selectedJob.result.models.M1_RandomForest.test_metrics.confusion_matrix.map((row, rIdx) => (
                          <div key={rIdx} style={{ display: 'flex', gap: '4px' }}>
                            {row.map((val, cIdx) => (
                              <span
                                key={cIdx}
                                className="te-cm-cell"
                                style={{ background: rIdx === cIdx ? 'rgba(2,132,199,.35)' : 'rgba(30,41,59,.4)' }}
                              >
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
                    <div className="te-card">
                      <h3 style={{ color: '#10b981', margin: '0 0 10px' }}>M2 (XGBoost) — Prueba Ciega</h3>
                      <div className="te-grid-3" style={{ marginBottom: '14px' }}>
                        <div className="te-metric-card">
                          <span>Accuracy</span>
                          <strong>{selectedJob.result.models.M2_XGBoost.test_metrics.accuracy}</strong>
                        </div>
                        <div className="te-metric-card">
                          <span>F1-Macro</span>
                          <strong>{selectedJob.result.models.M2_XGBoost.test_metrics.f1_macro}</strong>
                        </div>
                        <div className="te-metric-card">
                          <span>Precision Macro</span>
                          <strong>{selectedJob.result.models.M2_XGBoost.test_metrics.precision_macro}</strong>
                        </div>
                      </div>

                      <h4 style={{ margin: '12px 0 6px', fontSize: '12px' }}>Matriz de Confusión:</h4>
                      <div className="te-cm-grid">
                        {selectedJob.result.models.M2_XGBoost.test_metrics.confusion_matrix.map((row, rIdx) => (
                          <div key={rIdx} style={{ display: 'flex', gap: '4px' }}>
                            {row.map((val, cIdx) => (
                              <span
                                key={cIdx}
                                className="te-cm-cell"
                                style={{ background: rIdx === cIdx ? 'rgba(16,185,129,.35)' : 'rgba(30,41,59,.4)' }}
                              >
                                {val}
                              </span>
                            ))}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Gráficos Incrustados */}
                {selectedJob.result.charts && (
                  <div className="te-grid-2" style={{ marginTop: '16px' }}>
                    {Object.entries(selectedJob.result.charts).map(([cName, b64]) => (
                      <div key={cName} className="te-card" style={{ textAlign: 'center' }}>
                        <h4 style={{ margin: '0 0 10px', color: '#c0cedc' }}>
                          {cName.replace('_', ' ').toUpperCase()}
                        </h4>
                        <img
                          src={`data:image/png;base64,${b64}`}
                          alt={cName}
                          style={{ maxWidth: '100%', borderRadius: '6px', border: '1px solid rgba(158,190,221,.1)' }}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* TAB 7: COMPARACIÓN DE MODELOS */}
        {activeTab === 'comparison' && (
          <div className="te-tab-pane">
            <div className="te-card">
              <h3 style={{ margin: '0 0 12px', color: '#70e3e1' }}>Matriz Comparativa de Desempeño (M1 vs M2)</h3>
              <p style={{ color: '#8ea4ba', fontSize: '13px' }}>
                Comparación rigurosa sobre el conjunto de prueba ciego (15%) para el objetivo supervisado.
              </p>

              {selectedJob?.result?.comparison_table ? (
                <table className="te-table" style={{ marginTop: '14px' }}>
                  <thead>
                    <tr>
                      <th>Métrica</th>
                      <th>M1 (Random Forest)</th>
                      <th>M2 (XGBoost)</th>
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
                          <span
                            className="te-pill"
                            style={{
                              background: row.best_model.includes('M1')
                                ? 'rgba(2,132,199,.2)'
                                : row.best_model.includes('M2')
                                ? 'rgba(16,185,129,.2)'
                                : 'transparent',
                            }}
                          >
                            {row.best_model}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p style={{ color: '#8fa4bc' }}>No hay comparativas listas aún.</p>
              )}
            </div>

            {/* M3 Panel de Anomalías */}
            {selectedJob?.result?.models.M3_IsolationForest && (
              <div className="te-card" style={{ marginTop: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h4 style={{ margin: 0, color: '#f59e0b' }}>M3: Detección No Supervisada de Anomalías (Isolation Forest)</h4>
                  <span className="te-node-badge" style={{ background: '#f59e0b', color: '#000' }}>
                    {selectedJob.result.models.M3_IsolationForest.anomaly_rate_pct}% Cuentas Anómalas
                  </span>
                </div>
                <p style={{ color: '#94a9bf', fontSize: '12px', margin: '8px 0 14px' }}>
                  {selectedJob.result.models.M3_IsolationForest.methodological_note}
                </p>

                <h5 style={{ margin: '14px 0 8px', color: '#c0cedc' }}>Top Identidades con Mayor Desviación:</h5>
                <table className="te-table">
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Username</th>
                      <th>Dominio AD</th>
                      <th>Score Anomalía</th>
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
                        <td>{anom.is_admin ? '✓ Sí' : 'No'}</td>
                        <td>{anom.password_never_expires ? '⚠️ Sí' : 'No'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 8: REPORTES & TRAZABILIDAD */}
        {activeTab === 'reports' && (
          <div className="te-tab-pane">
            <div className="te-card">
              <h3 style={{ margin: '0 0 12px', color: '#70e3e1' }}>Exportación y Descarga de Reportes de Auditoría IA</h3>
              <p style={{ color: '#8ea4ba', fontSize: '13px' }}>
                Descarga de reportes reproducibles con firma de trazabilidad criptográfica (SHA-256), parámetros de
                entrenamiento y tablas de evaluación.
              </p>

              {selectedJob?.job_id ? (
                <div style={{ display: 'flex', gap: '14px', marginTop: '20px', flexWrap: 'wrap' }}>
                  <a
                    href={getReportDownloadUrl(selectedJob.job_id, 'pdf')}
                    target="_blank"
                    rel="noreferrer"
                    className="te-btn-download"
                    style={{ background: '#ef4444' }}
                  >
                    📄 Descargar Reporte PDF
                  </a>
                  <a
                    href={getReportDownloadUrl(selectedJob.job_id, 'docx')}
                    target="_blank"
                    rel="noreferrer"
                    className="te-btn-download"
                    style={{ background: '#2563eb' }}
                  >
                    📝 Descargar Reporte Word (.docx)
                  </a>
                  <a
                    href={getReportDownloadUrl(selectedJob.job_id, 'xlsx')}
                    target="_blank"
                    rel="noreferrer"
                    className="te-btn-download"
                    style={{ background: '#10b981' }}
                  >
                    📊 Descargar Reporte Excel (.xlsx)
                  </a>
                </div>
              ) : (
                <p style={{ color: '#8fa4bc' }}>Selecciona o completa un experimento para exportar reportes.</p>
              )}
            </div>

            {/* Historial de Experimentos */}
            <div className="te-card" style={{ marginTop: '16px' }}>
              <h4 style={{ margin: '0 0 12px' }}>Historial de Experimentos Registrados</h4>
              <table className="te-table">
                <thead>
                  <tr>
                    <th>ID de Experimento</th>
                    <th>Estado</th>
                    <th>Actor</th>
                    <th>Fecha</th>
                    <th>Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((j) => (
                    <tr key={j.job_id}>
                      <td><code>{j.job_id}</code></td>
                      <td>
                        <span className={`te-status-tag ${j.status}`}>
                          {j.status}
                        </span>
                      </td>
                      <td>{j.actor}</td>
                      <td>{j.created_at ? new Date(j.created_at).toLocaleString('es-PE') : '-'}</td>
                      <td>
                        <button
                          className="te-btn-sm"
                          onClick={async () => {
                            const full = await getTrainingJob(j.job_id)
                            setSelectedJob(full)
                            setActiveTab('metrics')
                          }}
                        >
                          Ver Detalles
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
    </div>
  )
}
