import { Loader2 } from 'lucide-react'
import type { FetchMoreState } from '../../types'

interface Props { state: FetchMoreState & { canFetchMore?: boolean }; loading: boolean; message: string | null; onFetch: () => void }

export function FetchMore({ state, loading, message, onFetch }: Props) {
  return (
    <div className="mt-14 flex flex-col items-center gap-3 text-center">
      {state.exhausted ? (
        <>
          <p className="text-lg font-medium">You've caught up with today's briefing.</p>
          <p className="max-w-md text-sm text-muted">Your next batch of important stories will be available with the next daily update.</p>
        </>
      ) : (
        <>
          <button type="button" onClick={onFetch} disabled={loading || state.canFetchMore === false}
            className="press inline-flex min-h-12 min-w-[200px] items-center justify-center gap-2 rounded-full bg-ink px-8 text-sm font-semibold text-bg disabled:opacity-50">
            {loading && <Loader2 size={16} className="animate-spin" aria-hidden />}
            {loading ? 'Fetching…' : 'Fetch More'}
          </button>
          <p className="text-xs text-muted">{state.remaining} of {state.max} extra batches left today</p>
        </>
      )}
      <p role="status" aria-live="polite" className="min-h-5 text-sm text-muted">{message}</p>
    </div>
  )
}
