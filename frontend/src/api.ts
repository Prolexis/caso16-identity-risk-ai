export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
).replace(/\/$/, '')

export type HealthResponse = {
  status?: string
  version?: string
  [key: string]: unknown
}

export type DashboardResponse = {
  kpis?: unknown
  updated_at?: string
  updatedAt?: string
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
