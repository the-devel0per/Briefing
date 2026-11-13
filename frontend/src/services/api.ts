import { API_BASE_URL } from '../config/env'
import type { Briefing, FetchMoreResponse, HumourMode, Preferences } from '../types'
import { clearSession, ensureSession } from './session'

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message) }
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const token = await ensureSession()
  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...(init.headers ?? {}) },
    })
  } catch {
    throw new ApiError(0, 'NETWORK', 'Network error. Check your connection and try again.')
  }
  if (res.status === 401 && retry) { clearSession(); return request<T>(path, init, false) }
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, data?.error?.code ?? 'UNKNOWN', data?.error?.message ?? 'Request failed')
  return data as T
}

export const getBriefing = (mode?: string) => request<Briefing>(mode ? `/api/briefing/today?mode=${encodeURIComponent(mode)}` : '/api/briefing/today')
export const savePreferences = (p: Preferences) => request<Preferences>('/api/preferences', { method: 'POST', body: JSON.stringify(p) })
export const fetchMore = (idempotencyKey: string) =>
  request<FetchMoreResponse>('/api/news/fetch-more', { method: 'POST', headers: { 'Idempotency-Key': idempotencyKey } })
export const rewriteHeadline = (id: string, mode: HumourMode) =>
  request<{ headline: string }>(`/api/news/${id}/rewrite`, { method: 'POST', body: JSON.stringify({ mode }) })

export interface ArticleSummary {
  articleId: string
  overview: string
  keyPoints: string[]
  cached?: boolean
  fallback?: boolean
}

export const getArticleSummary = (id: string) => request<ArticleSummary>(`/api/news/${id}/summary`)
