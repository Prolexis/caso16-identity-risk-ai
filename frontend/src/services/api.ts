import {
  AuditLogItem,
  DashboardResponse,
  DirectoryAccount,
  DirectorySource,
  EdaSummary,
  ExperimentJob,
  HealthResponse,
  RemediationTicket,
  SecurityFinding,
  SecurityPolicy,
  SystemRole,
  SystemUser,
  TrainingDefaultsConfig,
} from '../types'

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8001/api/v1'
).replace(/\/$/, '')

const getAuthToken = (): string | null => {
  return localStorage.getItem('caso16_auth_token')
}

export const setAuthToken = (token: string | null) => {
  if (token) {
    localStorage.setItem('caso16_auth_token', token)
  } else {
    localStorage.removeItem('caso16_auth_token')
  }
}

const request = async <T>(path: string, options?: RequestInit, timeoutMs = 12_000): Promise<T> => {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)

  const token = getAuthToken()
  const headers: Record<string, string> = {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((options?.headers as Record<string, string>) ?? {}),
  }

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers,
    })
    if (!response.ok) {
      const errBody = await response.text()
      throw new Error(`HTTP ${response.status}: ${errBody || response.statusText}`)
    }
    return (await response.json()) as T
  } finally {
    window.clearTimeout(timeout)
  }
}

// ==============================================================================
// 1. SALUD, DASHBOARD Y ESTADO
// ==============================================================================
export const getHealth = () => request<HealthResponse>('/health')
export const getDashboard = () => request<DashboardResponse>('/dashboard')
export const getSystemHealth = () => request<Record<string, unknown>>('/health/system')

// ==============================================================================
// 2. GESTIÓN DE IDENTIDADES Y CUENTAS
// ==============================================================================
export const getAccounts = (params?: { limit?: number; search?: string }) => {
  const query = new URLSearchParams()
  if (params?.limit) query.append('limit', String(params.limit))
  if (params?.search) query.append('search', params.search)
  const qs = query.toString() ? `?${query.toString()}` : ''
  return request<{ items: DirectoryAccount[]; total: number }>(`/accounts${qs}`)
}

export const updateAccountMetadata = (
  accountId: number,
  payload: { justification_verified?: boolean; privilege_justification?: string; review_at?: string }
) => request<{ status: string; account_id: number }>(`/accounts/${accountId}/metadata`, {
  method: 'PATCH',
  body: JSON.stringify(payload),
})

export const getDirectories = () => request<{ items: DirectorySource[]; total: number }>('/directories')

// ==============================================================================
// 3. HALLAZGOS Y REMEDIACIÓN
// ==============================================================================
export const getFindings = (params?: { status?: string; severity?: string; limit?: number }) => {
  const query = new URLSearchParams()
  if (params?.status) query.append('status', params.status)
  if (params?.severity) query.append('severity', params.severity)
  if (params?.limit) query.append('limit', String(params.limit))
  const qs = query.toString() ? `?${query.toString()}` : ''
  return request<{ items: SecurityFinding[]; total: number }>(`/findings${qs}`)
}

export const updateFindingStatus = (
  findingId: number,
  payload: { status: string; owner?: string; comment?: string; actor?: string; role?: string }
) => request<{ status: string; finding_id: string }>(`/findings/${findingId}`, {
  method: 'PATCH',
  body: JSON.stringify(payload),
})

export const explainFindingAi = (findingId: number) =>
  request<Record<string, unknown>>(`/ai/explain/${findingId}`, { method: 'POST' })

export const getTickets = (params?: { status?: string; priority?: string }) => {
  const query = new URLSearchParams()
  if (params?.status) query.append('status', params.status)
  if (params?.priority) query.append('priority', params.priority)
  const qs = query.toString() ? `?${query.toString()}` : ''
  return request<{ items: RemediationTicket[]; total: number }>(`/tickets${qs}`)
}

export const createTicket = (payload: {
  finding_id?: number | null
  title: string
  description: string
  priority?: string
  owner?: string
  sla_days?: number
}) => request<{ status: string; ticket_id: string }>('/tickets', {
  method: 'POST',
  body: JSON.stringify(payload),
})

export const updateTicket = (
  ticketId: string,
  payload: { status: string; owner?: string; resolution_notes?: string }
) => request<{ status: string; ticket_id: string }>(`/tickets/${ticketId}`, {
  method: 'PATCH',
  body: JSON.stringify(payload),
})

// ==============================================================================
// 4. MOTOR DE ENTRENAMIENTO IA (M1, M2, M3, EDA, OPTUNA)
// ==============================================================================
export const getEda = (useDemo = false) =>
  request<EdaSummary>(`/training/eda?use_demo=${useDemo}`)

export const getTrainingDefaults = () =>
  request<TrainingDefaultsConfig>('/training/config/defaults')

export const startTrainingExperiment = (payload: {
  run_m1: boolean
  run_m2: boolean
  run_m3: boolean
  use_optuna: boolean
  optuna_trials_m1: number
  optuna_trials_m2: number
  optuna_trials_m3: number
  timeout_seconds?: number
  seed: number
  stratify?: boolean
  use_demo_dataset: boolean
  actor?: string
  params_m1?: Record<string, unknown>
  params_m2?: Record<string, unknown>
  params_m3?: Record<string, unknown>
}) => request<{ status: string; job_id: string; message: string }>('/training/start', {
  method: 'POST',
  body: JSON.stringify(payload),
})

export const getTrainingJobs = () =>
  request<{ jobs: ExperimentJob[]; total: number }>('/training/jobs')

export const getTrainingJobDetail = (jobId: string) =>
  request<ExperimentJob>(`/training/jobs/${jobId}`)

export const cancelTrainingJob = (jobId: string) =>
  request<{ status: string; job_id: string; message: string }>(`/training/jobs/${jobId}/cancel`, {
    method: 'POST',
  })

export const getTrainingReportDownloadUrl = (jobId: string, format: 'pdf' | 'docx' | 'xlsx') =>
  `${API_BASE_URL}/training/jobs/${jobId}/report?format=${format}`

export const getGeneralReportDownloadUrl = (format: 'pdf' | 'docx' | 'xlsx') =>
  `${API_BASE_URL}/reports/export?format=${format}`

// ==============================================================================
// 5. AUDITORÍA, POLÍTICAS Y USUARIOS
// ==============================================================================
export const getAuditLogs = (limit = 100) =>
  request<{ items: AuditLogItem[]; total: number }>(`/audit?limit=${limit}`)

export const getPolicies = () =>
  request<{ items: SecurityPolicy[]; total: number }>('/policies')

export const updatePolicy = (policyId: number, payload: { threshold_value: number; is_active: boolean }) =>
  request<{ status: string; policy_id: string }>(`/policies/${policyId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })

export const getUsers = () => request<{ items: SystemUser[]; total: number }>('/users')
export const getRoles = () => request<{ items: SystemRole[]; total: number }>('/roles')
export const triggerN8n = () => request<Record<string, unknown>>('/integrations/n8n/trigger', { method: 'POST' })
