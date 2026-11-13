import { API_BASE_URL } from '../config/env'

const KEY = 'session_token'
let pending: Promise<string> | null = null

/** Anonymous bearer token issued by the backend. Treat it like a password: anyone holding it is "you". */
export async function ensureSession(): Promise<string> {
  const existing = localStorage.getItem(KEY)
  if (existing) return existing
  pending ??= fetch(`${API_BASE_URL}/api/session`, { method: 'POST' })
    .then(async (r) => {
      if (!r.ok) throw new Error('Could not start a session')
      const { token } = (await r.json()) as { token: string }
      localStorage.setItem(KEY, token)
      return token
    })
    .finally(() => { pending = null })
  return pending
}

export const clearSession = () => localStorage.removeItem(KEY)
export const getSyncCode = () => localStorage.getItem(KEY)
export const applySyncCode = (code: string) => {
  if (!/^v1\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(code.trim())) throw new Error('That sync code looks invalid')
  localStorage.setItem(KEY, code.trim())
}
