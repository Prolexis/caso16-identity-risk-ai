export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
).replace(/\/$/, '')

export type HealthResponse = {
  status?: string
  database?: string
  mode?: string
  source?: string
  accounts_loaded?: number
  [key: string]: unknown
}

export type DashboardResponse = {
  accounts?: number
  inactive?: number
  orphans?: number
  excessive?: number
  service_no_expiry?: number
  open_findings?: number
  closed_findings?: number
  risk_total?: number
  kpis?: unknown
  [key: string]: unknown
}

export type EdaResponse = {
  total_records: number
  dataset_hash?: string
  analyzed_at?: string
  status?: string
  columns_summary?: Array<{
    name: string
    dtype: string
    missing_count: number
    missing_pct: number
    unique_values: number
  }>
  integrity?: {
    duplicate_external_ids: number
    duplicate_usernames: number
    full_row_duplicates: number
  }
  active_directory_telemetry?: {
    attribute_evaluated: string
    accounts_without_logon: number
    accounts_without_logon_pct: number
    accounts_inactive_90_days_or_more: number
    accounts_inactive_90_days_or_more_pct: number
    ad_technical_warning: string
  }
  categorical_distributions?: {
    account_types: Record<string, number>
    sources_domains: Record<string, number>
    security_flags: Record<string, { true_count: number; false_count: number; true_pct: number }>
  }
  numeric_dispersion?: Record<string, {
    mean: number
    std: number
    median: number
    min: number
    max: number
    q1: number
    q3: number
    iqr: number
    outliers_count: number
  }>
  target_class_distribution?: {
    classes: Record<string, { count: number; percentage: number }>
    imbalance_ratio: number
    minority_class_count: number
  }
  recommendations?: string[]
}

export type TrainingDefaults = {
  m1_random_forest: {
    name: string
    type: string
    defaults: Record<string, unknown>
    optuna_search_space: Record<string, unknown>
    stopping_condition: string
    rationale: string
  }
  m2_xgboost: {
    name: string
    type: string
    defaults: Record<string, unknown>
    optuna_search_space: Record<string, unknown>
    stopping_condition: string
    rationale: string
  }
  m3_isolation_forest: {
    name: string
    type: string
    defaults: Record<string, unknown>
    optuna_search_space: Record<string, unknown>
    stopping_condition: string
    rationale: string
  }
}

export type TrainingJob = {
  job_id: string
  status: string
  actor: string
  progress: {
    stage?: string
    percent?: number
    message?: string
    timestamp?: string
  }
  created_at: string
  has_result?: boolean
  error?: string | null
  result?: {
    experiment_id: string
    elapsed_seconds: number
    dataset_hash: string
    total_records: number
    partition: {
      train_count: number
      val_count: number
      test_count: number
      train_pct: number
      val_pct: number
      test_pct: number
      stratified: boolean
    }
    models: {
      M1_RandomForest?: {
        model_type: string
        hyperparameters: Record<string, unknown>
        validation_metrics: Record<string, unknown>
        test_metrics: {
          accuracy: number
          precision_macro: number
          recall_macro: number
          f1_macro: number
          f1_weighted: number
          mcc: number
          roc_auc?: number
          pr_auc?: number
          classes: string[]
          confusion_matrix: number[][]
          confusion_matrix_normalized: number[][]
        }
        feature_importance: Record<string, number>
        stopping_condition: string
      }
      M2_XGBoost?: {
        model_type: string
        hyperparameters: Record<string, unknown>
        validation_metrics: Record<string, unknown>
        test_metrics: {
          accuracy: number
          precision_macro: number
          recall_macro: number
          f1_macro: number
          f1_weighted: number
          mcc: number
          roc_auc?: number
          pr_auc?: number
          classes: string[]
          confusion_matrix: number[][]
          confusion_matrix_normalized: number[][]
        }
        feature_importance: Record<string, number>
        stopping_condition: string
      }
      M3_IsolationForest?: {
        model_type: string
        hyperparameters: Record<string, unknown>
        total_evaluated: number
        anomalies_detected: number
        anomaly_rate_pct: number
        top_anomalies: Array<{
          rank: number
          username: string
          source: string
          anomaly_score: number
          deterministic_risk_score: number
          is_admin: boolean
          password_never_expires: boolean
        }>
        methodological_note: string
        stopping_condition: string
      }
    }
    optuna_studies?: Record<string, {
      best_value: number
      best_params: Record<string, unknown>
      trials_count: number
      trials_history: Array<{ trial: number; score: number; params: Record<string, unknown> }>
    }>
    comparison_table: Array<{
      metric: string
      m1_random_forest: number | null
      m2_xgboost: number | null
      best_model: string
    }>
    charts?: Record<string, string>
    methodology_diagram?: {
      phases: Array<{ step: number; name: string; status: string; detail: string }>
    }
  }
}

const request = async <T>(path: string, options?: RequestInit, timeoutMs = 12_000): Promise<T> => {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        ...(options?.headers ?? {}),
      },
    })
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    return (await response.json()) as T
  } finally {
    window.clearTimeout(timeout)
  }
}

export const getHealth = () => request<HealthResponse>('/health')
export const getDashboard = () => request<DashboardResponse>('/dashboard')

// Training Engine API
export const getEda = (useDemo = false) => request<EdaResponse>(`/training/eda?use_demo=${useDemo}`)
export const getTrainingDefaults = () => request<TrainingDefaults>('/training/config/defaults')
export const startTraining = (payload: {
  run_m1: boolean
  run_m2: boolean
  run_m3: boolean
  use_optuna: boolean
  optuna_trials_m1: number
  optuna_trials_m2: number
  optuna_trials_m3: number
  seed: number
  use_demo_dataset: boolean
  params_m1?: Record<string, unknown>
  params_m2?: Record<string, unknown>
  params_m3?: Record<string, unknown>
}) => request<{ status: string; job_id: string; message: string }>('/training/start', {
  method: 'POST',
  body: JSON.stringify(payload),
})
export const getTrainingJobs = () => request<{ jobs: TrainingJob[]; total: number }>('/training/jobs')
export const getTrainingJob = (jobId: string) => request<TrainingJob>(`/training/jobs/${jobId}`)
export const cancelTrainingJob = (jobId: string) => request<{ status: string; job_id: string; message: string }>(`/training/jobs/${jobId}/cancel`, {
  method: 'POST',
})
export const getReportDownloadUrl = (jobId: string, format: 'pdf' | 'docx' | 'xlsx') =>
  `${API_BASE_URL}/training/jobs/${jobId}/report?format=${format}`
