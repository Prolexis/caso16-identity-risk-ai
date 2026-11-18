export type ThemeMode = 'dark' | 'light'

export type NavItemKey =
  | 'dashboard'
  | 'security-monitor'
  | 'identities'
  | 'orphans'
  | 'excessive-privs'
  | 'directories'
  | 'ai-training-center'
  | 'ai-eda'
  | 'ai-models-config'
  | 'ai-execution'
  | 'ai-evaluation'
  | 'ai-comparison'
  | 'ai-explainability'
  | 'findings'
  | 'tickets'
  | 'rules'
  | 'automation'
  | 'reports'
  | 'audit'
  | 'policies'
  | 'users-roles'

export type UserRole =
  | 'Superadministrador'
  | 'Administrador de seguridad'
  | 'Analista de ciberseguridad'
  | 'Responsable de remediación'
  | 'Auditor'
  | 'Usuario de consulta'

export interface UserProfile {
  username: string
  email: string
  fullName: string
  role: UserRole
}

export interface HealthResponse {
  status: string
  database: string
  mode: string
  integrations?: string
  source?: string
  accounts_loaded: number
  findings_active?: number
  tickets_managed?: number
  users_rbac?: number
  [key: string]: unknown
}

export interface DashboardResponse {
  accounts?: number
  inactive?: number
  orphans?: number
  excessive?: number
  service_no_expiry?: number
  open_findings?: number
  closed_findings?: number
  risk_total?: number
  critical_findings?: number
  high_findings?: number
  medium_findings?: number
  low_findings?: number
  [key: string]: unknown
}

export interface DirectoryAccount {
  id: number
  external_id: string
  username: string
  display_name: string
  email: string | null
  account_type: 'user' | 'service' | string
  source: string
  active: boolean
  is_admin: boolean
  justification_verified: boolean
  is_duplicate: boolean
  password_never_expires: boolean
  privileged_roles: string
  last_activity: string | null
  review_at: string | null
  risk_score: number
  created_at?: string
}

export interface SecurityFinding {
  id: number
  account_id: number
  rule_id: string
  title: string
  severity: 'Crítico' | 'Alto' | 'Medio' | 'Bajo'
  evidence_state: string
  status: 'Detectado' | 'En revisión' | 'Remediado' | 'Cerrado' | 'En proceso'
  rationale: string
  evidence: string
  risk_score: number
  owner: string | null
  created_at: string
  updated_at: string
}

export interface RemediationTicket {
  id: string
  finding_id: number | null
  title: string
  description: string
  status: 'Abierto' | 'En progreso' | 'Resuelto' | 'Cerrado'
  priority: 'Crítica' | 'Alta' | 'Media' | 'Baja'
  owner: string | null
  sla_due_date: string
  resolution_notes?: string | null
  created_at: string
  updated_at: string
}

export interface AuditLogItem {
  id: number
  actor: string
  role: string
  action: string
  resource: string
  result: 'success' | 'failed' | 'denied' | string
  details: string
  ip_address: string
  occurred_at: string
}

export interface SecurityPolicy {
  id: number
  code: string
  name: string
  description: string
  threshold_value: number
  unit: string
  is_active: boolean
  updated_at: string
}

export interface DirectorySource {
  id: number
  name: string
  domain: string
  server_url: string
  use_tls: boolean
  status: string
  accounts_count: number
  last_sync_at: string
}

export interface SystemUser {
  id: number
  username: string
  email: string
  full_name: string
  role: string
  active: boolean
  created_at: string
}

export interface SystemRole {
  id: number
  name: string
  description: string
  permissions: string
  created_at: string
}

// ==============================================================================
// TIPOS MOTOR DE ENTRENAMIENTO IA
// ==============================================================================

export interface EdaSummary {
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

export interface TrainingDefaultsConfig {
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

export interface ExperimentJob {
  job_id: string
  status: 'running' | 'completed' | 'failed' | 'cancelled' | string
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
