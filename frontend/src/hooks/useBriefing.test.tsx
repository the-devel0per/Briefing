import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { article } from '../test/fixtures'
import type { Briefing } from '../types'

vi.mock('../services/api', () => {
  class ApiError extends Error { constructor(public status: number, public code: string, m: string) { super(m) } }
  return { ApiError, getBriefing: vi.fn(), savePreferences: vi.fn(), fetchMore: vi.fn(), rewriteHeadline: vi.fn() }
})
import * as api from '../services/api'
import { useBriefing } from './useBriefing'

const briefing = (over: Partial<Briefing> = {}): Briefing => ({
  date: '2026-11-13', lastUpdated: null, target: 10, total: 1, articles: [article()], activeCategories: ['technology'],
  categoryCounts: { technology: 1, government: 0, crypto: 0, stocks: 0 }, notice: null,
  preferences: { mutedCategories: [], humourMode: 'witty' },
  fetchMore: { used: 0, max: 2, remaining: 2, exhausted: false, canFetchMore: true }, ...over,
})

describe('useBriefing', () => {
  beforeEach(() => { vi.resetAllMocks() })

  it('loads the briefing', async () => {
    vi.mocked(api.getBriefing).mockResolvedValue(briefing())
    const { result } = renderHook(() => useBriefing())
    expect(result.current.status).toBe('loading')
    await waitFor(() => expect(result.current.status).toBe('ready'))
    expect(result.current.articles).toHaveLength(1)
  })

  it('surfaces an error state', async () => {
    vi.mocked(api.getBriefing).mockRejectedValue(new Error('boom'))
    const { result } = renderHook(() => useBriefing())
    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.error).toBe('boom')
  })

  it('appends unique fetched stories and marks exhausted from the server state', async () => {
    vi.mocked(api.getBriefing).mockResolvedValue(briefing())
    vi.mocked(api.fetchMore).mockResolvedValue({
      articles: [article(), article({ id: 'b'.repeat(16) })], replayed: false,
      fetchMore: { used: 2, max: 2, remaining: 0, exhausted: true },
    })
    const { result } = renderHook(() => useBriefing())
    await waitFor(() => expect(result.current.status).toBe('ready'))
    await act(async () => { await result.current.loadMore() })
    expect(result.current.articles).toHaveLength(2) // duplicate id ignored
    expect(result.current.fetchMore?.exhausted).toBe(true)
  })

  it('treats the server quota error as exhausted without calling again', async () => {
    vi.mocked(api.getBriefing).mockResolvedValue(briefing())
    vi.mocked(api.fetchMore).mockRejectedValue(new api.ApiError(429, 'FETCH_MORE_LIMIT_REACHED', 'limit'))
    const { result } = renderHook(() => useBriefing())
    await waitFor(() => expect(result.current.status).toBe('ready'))
    await act(async () => { await result.current.loadMore() })
    expect(result.current.fetchMore?.exhausted).toBe(true)
    await act(async () => { await result.current.loadMore() })
    expect(api.fetchMore).toHaveBeenCalledTimes(1)
  })

  it('saves preferences then reloads (muted slots are reallocated server-side)', async () => {
    vi.mocked(api.getBriefing).mockResolvedValue(briefing())
    vi.mocked(api.savePreferences).mockResolvedValue({ mutedCategories: ['crypto'], humourMode: 'witty' })
    const { result } = renderHook(() => useBriefing())
    await waitFor(() => expect(result.current.status).toBe('ready'))
    await act(async () => { await result.current.updatePrefs({ mutedCategories: ['crypto'], humourMode: 'witty' }) })
    expect(api.savePreferences).toHaveBeenCalled()
    expect(api.getBriefing).toHaveBeenCalledTimes(2)
  })
})
