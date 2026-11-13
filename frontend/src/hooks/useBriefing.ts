import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import * as api from '../services/api'
import { ApiError } from '../services/api'
import type { Article, Briefing, FetchMoreState, HumourMode, Preferences } from '../types'

export const ACTIVE_MODES: HumourMode[] = ['sarcastic', 'genz', 'unhinged']

export function getRandomMode(): HumourMode {
  return ACTIVE_MODES[Math.floor(Math.random() * ACTIVE_MODES.length)]
}

export function useBriefing() {
  const [selectedTone, setSelectedTone] = useState<HumourMode>(() => getRandomMode())
  const [briefing, setBriefing] = useState<Briefing | null>(null)
  const [articles, setArticles] = useState<Article[]>([])
  const [fetchMore, setFetchMore] = useState<FetchMoreState | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [fetching, setFetching] = useState(false)
  const [moreMessage, setMoreMessage] = useState<string | null>(null)
  const [rewrites, setRewrites] = useState<Record<string, string>>({})
  const inFlight = useRef(false)

  const tone = selectedTone
  const toneRef = useRef(selectedTone)
  toneRef.current = selectedTone

  const load = useCallback(async (silent = false, toneOverride?: HumourMode) => {
    if (!silent) setStatus('loading')
    const queryTone = toneOverride ?? toneRef.current
    try {
      const b = await api.getBriefing(queryTone)
      setBriefing({
        ...b,
        preferences: {
          ...b.preferences,
          humourMode: queryTone,
        },
      })
      setArticles(b.articles)
      setFetchMore(b.fetchMore)
      setStatus('ready')
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong')
      if (!silent) setStatus('error')
    } finally {
      setRefreshing(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const updatePrefs = useCallback(async (next: Preferences) => {
    setSelectedTone(next.humourMode)
    setBriefing((b) => (b ? { ...b, preferences: next } : b))
    setRefreshing(true)
    try {
      await api.savePreferences(next)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save')
    }
    await load(true, next.humourMode)
  }, [load])

  const loadMore = useCallback(async () => {
    if (inFlight.current || !fetchMore || fetchMore.exhausted) return
    inFlight.current = true
    setFetching(true)
    setMoreMessage(null)
    const key = crypto.randomUUID()
    try {
      const r = await api.fetchMore(key)
      setArticles((prev) => [...prev, ...r.articles.filter((a) => !prev.some((p) => p.id === a.id))])
      setFetchMore(r.fetchMore)
      setMoreMessage(r.articles.length ? `Added ${r.articles.length} more stories.` : 'No more important stories right now.')
    } catch (e) {
      if (e instanceof ApiError && e.code === 'FETCH_MORE_LIMIT_REACHED') {
        setFetchMore((f) => (f ? { ...f, remaining: 0, exhausted: true } : f))
      } else {
        setMoreMessage(e instanceof Error ? e.message : 'Could not load more stories.')
      }
    } finally {
      inFlight.current = false
      setFetching(false)
    }
  }, [fetchMore])

  // Rewrites on-demand for any articles missing a rewrite for the active tone
  useEffect(() => {
    let cancelled = false
    void (async () => {
      const pending = articles.filter((a) => (!a.aiHeadline || a.aiMode !== tone) && !rewrites[`${tone}:${a.id}`])
      if (pending.length === 0) return
      const concurrency = 3
      for (let i = 0; i < pending.length; i += concurrency) {
        if (cancelled) return
        const batch = pending.slice(i, i + concurrency)
        let shouldStop = false
        await Promise.all(
          batch.map(async (a) => {
            try {
              const r = await api.rewriteHeadline(a.id, tone)
              if (!cancelled && r.headline) {
                setRewrites((prev) => ({ ...prev, [`${tone}:${a.id}`]: r.headline }))
              }
            } catch (e) {
              if (
                e instanceof ApiError &&
                (e.status === 429 || e.code === 'REWRITE_QUOTA_REACHED')
              ) {
                shouldStop = true
              }
            }
          })
        )
        if (shouldStop) break
      }
    })()
    return () => {
      cancelled = true
    }
  }, [tone, articles.length, briefing?.date, articles])

  const view = useMemo(
    () =>
      articles.map((a) =>
        rewrites[`${tone}:${a.id}`]
          ? { ...a, aiHeadline: rewrites[`${tone}:${a.id}`], aiMode: tone }
          : a
      ),
    [articles, rewrites, tone]
  )

  return {
    briefing,
    articles: view,
    fetchMore,
    status,
    error,
    refreshing,
    fetching,
    moreMessage,
    reload: load,
    updatePrefs,
    loadMore,
  }
}
