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

const request = async <T>(path: string, timeoutMs = 4_500): Promise<T> => {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      signal: controller.signal,
      headers: { Accept: 'application/json' },
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
