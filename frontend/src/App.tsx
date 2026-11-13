import { useState } from 'react'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { CardSkeleton, CategorySkeleton, FeedSkeleton } from './components/Skeleton'
import { ArticleCard } from './features/articles/ArticleCard'
import { SummaryModal } from './features/articles/SummaryModal'
import { BriefingHeader } from './features/briefing/BriefingHeader'
import { FetchMore } from './features/briefing/FetchMore'
import { CategoryPanel } from './features/categories/CategoryPanel'
import { useBriefing } from './hooks/useBriefing'
import { useTheme } from './hooks/useTheme'
import type { Article } from './types'

export default function App() {
  const { theme, toggle } = useTheme()
  const b = useBriefing()
  const [summaryArticle, setSummaryArticle] = useState<Article | null>(null)

  return (
    <>
      <a href="#feed" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-30 focus:rounded-ctl focus:bg-ink focus:px-4 focus:py-2 focus:text-bg">Skip to stories</a>
      <Header theme={theme} onToggleTheme={toggle} />
      <main className="mx-auto max-w-page px-5 sm:px-8">
        <BriefingHeader briefing={b.briefing} count={b.articles.length}>
          {b.briefing ? (
            <CategoryPanel
              preferences={b.briefing.preferences}
              counts={b.briefing.categoryCounts}
              onChange={b.updatePrefs}
            />
          ) : (
            <CategorySkeleton />
          )}
        </BriefingHeader>

        {b.status === 'loading' && <FeedSkeleton />}

        {b.status === 'error' && (
          <div role="alert" className="rounded-card border border-line bg-surface p-8 text-center">
            <p className="font-medium">We couldn't load your briefing.</p>
            <p className="mt-1 text-sm text-muted">{b.error}</p>
            <button type="button" onClick={() => b.reload()} className="press mt-4 h-11 rounded-full bg-ink px-6 text-sm font-semibold text-bg">Try again</button>
          </div>
        )}

        {b.status === 'ready' && b.briefing && (
          <>
            {b.error && <p role="alert" className="mb-4 text-sm text-muted">{b.error}</p>}
            {b.briefing.notice && <p className="mb-6 rounded-ctl border border-line bg-surface px-4 py-3 text-sm text-muted">{b.briefing.notice}</p>}
            <section id="feed" aria-label="Stories" aria-busy={b.refreshing}
              className={`grid gap-6 transition-opacity duration-300 md:grid-cols-2 lg:grid-cols-3 ${b.refreshing ? 'opacity-50' : 'opacity-100'}`}>
              {b.articles.map((a, i) => (
                <ArticleCard
                  key={a.id}
                  article={a}
                  lead={i === 0}
                  index={i}
                  onOpenSummary={setSummaryArticle}
                />
              ))}
              {b.fetching && Array.from({ length: 3 }).map((_, i) => (
                <CardSkeleton key={`fetch-skeleton-${i}`} />
              ))}
            </section>
            {b.articles.length === 0 && (
              <p className="py-16 text-center text-muted">No stories yet. The first update of the day is on its way.</p>
            )}
            {b.fetchMore && b.articles.length > 0 && (
              <FetchMore state={b.fetchMore} loading={b.fetching} message={b.moreMessage} onFetch={b.loadMore} />
            )}
          </>
        )}
      </main>
      <SummaryModal article={summaryArticle} onClose={() => setSummaryArticle(null)} />
      <Footer />
    </>
  )
}
