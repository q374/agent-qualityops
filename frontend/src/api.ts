import type { ApiErrorShape, AuditEvent, EvalCase, EvalRun, HumanReview, PromptVersion } from './types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') || '/api'

export class ApiError extends Error {
  status: number
  constructor(message: string, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function errorMessage(body: ApiErrorShape | null, status: number) {
  if (typeof body?.detail === 'string') return body.detail
  if (Array.isArray(body?.detail)) return body.detail.map((v) => v.msg || '参数错误').join('；')
  return body?.message || `请求失败（HTTP ${status}）`
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch {
    throw new ApiError('无法连接后端服务，请确认 FastAPI 已在 8000 端口启动。')
  }
  const text = await response.text()
  let body: unknown = null
  try { body = text ? JSON.parse(text) : null } catch { body = text }
  if (!response.ok) throw new ApiError(errorMessage(body as ApiErrorShape | null, response.status), response.status)
  return body as T
}

export function asList<T>(payload: unknown): T[] {
  if (Array.isArray(payload)) return payload as T[]
  if (payload && typeof payload === 'object') {
    for (const key of ['items', 'data', 'cases', 'versions', 'runs', 'results', 'badcases']) {
      const value = (payload as Record<string, unknown>)[key]
      if (Array.isArray(value)) return value as T[]
    }
  }
  return []
}

export const api = {
  health: () => request<Record<string, unknown>>('/health'),
  summary: () => request<Record<string, unknown>>('/summary'),
  cases: () => request<unknown>('/cases').then(asList<EvalCase>),
  importCases: (cases: Omit<EvalCase, 'id'>[]) => request<unknown>('/cases/import', { method: 'POST', body: JSON.stringify({ cases }) }),
  versions: () => request<unknown>('/versions').then(asList<PromptVersion>),
  createVersion: (payload: Omit<PromptVersion, 'id'>) => request<PromptVersion>('/versions', { method: 'POST', body: JSON.stringify(payload) }),
  runs: () => request<unknown>('/runs').then(asList<EvalRun>),
  createRun: (payload: { version_ids: number[]; case_ids?: number[]; mode: string; budget_cny: number }) => request<unknown>('/runs', { method: 'POST', body: JSON.stringify(payload) }),
  run: (id: number) => request<Record<string, unknown>>(`/runs/${id}`),
  compare: (baseline: number, candidate: number) => request<Record<string, unknown>>(`/compare?baseline_run_id=${baseline}&candidate_run_id=${candidate}`),
  badcases: (runId: number) => request<unknown>(`/badcases?run_id=${runId}`).then(asList),
  review: (resultId: number, payload: HumanReview) => request<unknown>(`/results/${resultId}/review`, { method: 'POST', body: JSON.stringify(payload) }),
  gate: (candidate: number, baseline: number) => request<Record<string, unknown>>(`/release-gates/${candidate}?baseline_run_id=${baseline}`),
  report: (runId: number) => request<Record<string, unknown>>(`/reports/${runId}`),
  auditEvents: (action = '') => {
    const query = new URLSearchParams({ limit: '100' })
    if (action) query.set('action', action)
    return request<unknown>(`/audit-events?${query}`).then(asList<AuditEvent>)
  },
}
