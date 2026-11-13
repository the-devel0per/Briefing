import { ArrowUpRight, Sparkles, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { categoryMeta } from '../../config/categories'
import { getArticleSummary, type ArticleSummary } from '../../services/api'
import type { Article } from '../../types'
import { timeAgo } from '../../utils/time'

interface Props {
  article: Article | null
  onClose: () => void
}

function formatBullet(text: string) {
  const colonIdx = text.indexOf(':')
  if (colonIdx > 0 && colonIdx < 40) {
    const lead = text.slice(0, colonIdx + 1)
    const rest = text.slice(colonIdx + 1)
    return (
      <>
        <strong className="font-semibold text-ink tracking-tight">{lead}</strong>
        <span className="text-muted leading-relaxed">{rest}</span>
      </>
    )
  }
  return <span className="text-muted leading-relaxed">{text}</span>
}

export function SummaryModal({ article, onClose }: Props) {
  const [summary, setSummary] = useState<ArticleSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!article) {
      setSummary(null)
      setError(null)
      return
    }

    let cancelled = false
    setLoading(true)
    setError(null)

    void (async () => {
      try {
        const res = await getArticleSummary(article.id)
        if (!cancelled) {
          setSummary(res)
        }
      } catch {
        if (!cancelled) {
          setError('Could not generate AI summary right now. You can read the original story below.')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [article])

  // Close on ESC key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  if (!article) return null

  const { Icon, label } = categoryMeta(article.category)

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="summary-modal-title"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 md:p-8 bg-black/40 dark:bg-black/80 backdrop-blur-md transition-opacity duration-200">
      <div
        onClick={(e) => e.stopPropagation()}
        className="relative flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-3xl border border-line dark:border-white/10 bg-card p-6 sm:p-9 shadow-2xl dark:shadow-[0_25px_60px_-15px_rgba(0,0,0,0.8)] transition-all">
        {/* Top bar */}
        <div className="flex items-center justify-between gap-3 pb-4 border-b border-line">
          <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3.5 py-1 text-xs font-semibold uppercase tracking-wider text-muted">
            <Icon size={14} aria-hidden className="text-ink" /> {label}
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close summary modal"
            className="press grid h-10 w-10 place-items-center rounded-full border border-line bg-card text-muted hover:border-ink hover:text-ink hover:bg-surface2 transition-all">
            <X size={18} />
          </button>
        </div>

        {/* Scrollable body content */}
        <div className="overflow-y-auto pr-1 mt-5 space-y-6">
          {/* Headline */}
          <div>
            <h3 id="summary-modal-title" className="text-2xl font-bold leading-snug tracking-tight text-ink sm:text-[28px] sm:leading-[1.25]">
              {article.aiHeadline || article.originalTitle}
            </h3>
            {article.aiHeadline && (
              <p className="mt-2 text-sm text-muted leading-normal">
                <span className="font-semibold uppercase tracking-wider text-[11px] text-muted">Original:</span> {article.originalTitle}
              </p>
            )}
          </div>

          {/* Executive Briefing Section */}
          <div className="space-y-4 rounded-2xl border border-line bg-surface p-5 sm:p-6">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-amber-500">
              <Sparkles size={16} />
              <span>Executive Briefing</span>
            </div>

            {loading ? (
              <div className="space-y-4 py-2 animate-pulse" aria-busy="true" aria-label="Loading summary">
                <div className="h-5 bg-surface2 rounded w-full" />
                <div className="h-5 bg-surface2 rounded w-4/5" />
                <div className="space-y-3 pt-3">
                  <div className="h-4 bg-surface2 rounded w-11/12" />
                  <div className="h-4 bg-surface2 rounded w-5/6" />
                  <div className="h-4 bg-surface2 rounded w-4/5" />
                </div>
              </div>
            ) : error ? (
              <div className="rounded-xl border border-line bg-card p-5 text-sm text-muted">
                {error}
              </div>
            ) : summary ? (
              <div className="space-y-5">
                {/* 1-2 lines high-signal overview */}
                <p className="text-base sm:text-[17px] font-medium leading-[1.65] text-ink">
                  {summary.overview}
                </p>

                {/* 3-4 key bullet points with bold lead phrases */}
                {summary.keyPoints && summary.keyPoints.length > 0 && (
                  <ul className="space-y-3.5 pt-1">
                    {summary.keyPoints.map((point, idx) => (
                      <li key={idx} className="flex items-start gap-3 text-sm sm:text-[15px] leading-[1.6]">
                        <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-amber-500 shadow-sm" />
                        <div>{formatBullet(point)}</div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : (
              <p className="text-base text-muted leading-relaxed">
                {article.summary || article.originalTitle}
              </p>
            )}
          </div>
        </div>

        {/* Footer info & CTA */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-line pt-4 text-xs sm:text-sm text-muted">
          <span>
            {article.publisher} · <time dateTime={article.publishedAt}>{timeAgo(article.publishedAt)}</time>
          </span>
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="press inline-flex min-h-11 items-center gap-2 rounded-full border border-line bg-card px-5 text-xs sm:text-sm font-semibold hover:border-ink hover:bg-surface2 text-ink transition-all">
            Read original source <ArrowUpRight size={15} />
          </a>
        </div>
      </div>
    </div>
  )
}

