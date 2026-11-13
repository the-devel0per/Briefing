import { ArrowUpRight, Sparkles } from 'lucide-react'
import { useMemo, useState } from 'react'
import { categoryMeta } from '../../config/categories'
import type { Article, CategoryId } from '../../types'
import { timeAgo } from '../../utils/time'

function hashString(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash) + str.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash)
}

function getTopicFallbackImage(category: CategoryId, title: string, id: string = '', index: number = 0): { url: string; attribution: string } {
  const lower = title.toLowerCase()
  const seed = (hashString(id || title) + index * 13)

  const pick = (list: Array<{ url: string; attribution: string }>) => list[seed % list.length]

  if (category === 'crypto') {
    if (lower.includes('hack') || lower.includes('stolen') || lower.includes('heist') || lower.includes('sec') || lower.includes('fraud')) {
      return pick([
        { url: 'https://images.unsplash.com/photo-1563986768609-322da13575f3?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Crypto Security' },
        { url: 'https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Cyber Defense' },
        { url: 'https://images.unsplash.com/photo-1614064641938-3bbee52942c7?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Digital Security' },
      ])
    }
    if (lower.includes('bitcoin') || lower.includes('btc')) {
      return pick([
        { url: 'https://images.unsplash.com/photo-1516245834210-c4c142787335?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Bitcoin' },
        { url: 'https://images.unsplash.com/photo-1622979135225-d2ba269bc1df?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Bitcoin Network' },
      ])
    }
    return pick([
      { url: 'https://images.unsplash.com/photo-1621416894569-0f39ed31d247?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Crypto Assets' },
      { url: 'https://images.unsplash.com/photo-1642790551116-18e150f248e3?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Blockchain' },
      { url: 'https://images.unsplash.com/photo-1622979135225-d2ba269bc1df?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Digital Finance' },
    ])
  }

  if (category === 'technology') {
    if (lower.includes('chip') || lower.includes('nvidia') || lower.includes('semiconductor') || lower.includes('hardware') || lower.includes('intel')) {
      return pick([
        { url: 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Semiconductor' },
        { url: 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Microchips' },
        { url: 'https://images.unsplash.com/photo-1591488320449-011701bb6704?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Silicon Wafer' },
      ])
    }
    if (lower.includes('ai') || lower.includes('openai') || lower.includes('chatgpt') || lower.includes('anthropic') || lower.includes('model') || lower.includes('software')) {
      return pick([
        { url: 'https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Artificial Intelligence' },
        { url: 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Neural Computing' },
        { url: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Generative AI' },
      ])
    }
    return pick([
      { url: 'https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Technology' },
      { url: 'https://images.unsplash.com/photo-1504384308090-c894fdcc538d?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Tech Innovations' },
      { url: 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Digital Future' },
    ])
  }

  if (category === 'stocks') {
    if (lower.includes('fed') || lower.includes('rate') || lower.includes('inflation') || lower.includes('bank') || lower.includes('treasury') || lower.includes('yield')) {
      return pick([
        { url: 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Financial Markets' },
        { url: 'https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Wall Street' },
        { url: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Financial District' },
        { url: 'https://images.unsplash.com/photo-1559526324-4b87b5e36e44?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Yield Analysis' },
        { url: 'https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Central Banking' },
      ])
    }
    if (lower.includes('drop') || lower.includes('fall') || lower.includes('crash') || lower.includes('slump')) {
      return pick([
        { url: 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Market Volatility' },
        { url: 'https://images.unsplash.com/photo-1535320903710-d993d3d77d29?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Market Downturn' },
      ])
    }
    return pick([
      { url: 'https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Wall Street' },
      { url: 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Trading Floor' },
      { url: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Global Equities' },
    ])
  }

  if (category === 'government') {
    if (lower.includes('court') || lower.includes('judge') || lower.includes('lawsuit') || lower.includes('legal') || lower.includes('justice')) {
      return pick([
        { url: 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Justice & Law' },
        { url: 'https://images.unsplash.com/photo-1575320181282-9afab399332c?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Judicial Chamber' },
      ])
    }
    if (lower.includes('treaty') || lower.includes('foreign') || lower.includes('summit') || lower.includes('war') || lower.includes('un')) {
      return pick([
        { url: 'https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Policy & Diplomacy' },
        { url: 'https://images.unsplash.com/photo-1520607162513-77705c0f0d4a?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · International Summit' },
      ])
    }
    return pick([
      { url: 'https://images.unsplash.com/photo-1541872703-74c5e44368f9?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Capitol Dome' },
      { url: 'https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?auto=format&fit=crop&w=1200&q=80', attribution: 'Unsplash · Public Policy' },
    ])
  }

  return {
    url: 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80',
    attribution: 'Unsplash',
  }
}

interface Props {
  article: Article
  lead?: boolean
  index?: number
  onOpenSummary?: (a: Article) => void
}

export function ArticleCard({ article: a, lead = false, index = 0, onOpenSummary }: Props) {
  const [loaded, setLoaded] = useState(false)
  const [broken, setBroken] = useState(false)
  const { Icon, label } = categoryMeta(a.category)
  const showImage = a.image && !broken

  const fallbackPhoto = useMemo(() => getTopicFallbackImage(a.category, a.originalTitle, a.id, index), [a.category, a.originalTitle, a.id, index])

  return (
    <article
      style={{ animationDelay: `${Math.min(index, 9) * 60}ms` }}
      className={`group animate-reveal flex flex-col overflow-hidden rounded-card border border-line bg-card transition-colors hover:border-muted ${lead ? 'lg:col-span-2 lg:flex-row' : ''}`}>
      <div className={`relative overflow-hidden bg-surface2 ${lead ? 'lg:w-3/5 lg:self-stretch' : ''}`}>
        {/* aspect-ratio reserves the space up front on vertical cards; stretches cleanly on horizontal lead cards */}
        <div className={`w-full ${lead ? 'aspect-[16/10] lg:aspect-auto lg:h-full' : 'aspect-[16/10]'}`}>
          {showImage ? (
            <>
              {!loaded && <div className="skeleton absolute inset-0" aria-hidden />}
              <img src={a.image!.url} alt={a.image!.alt} width={1200} height={750} loading={index < 2 ? 'eager' : 'lazy'}
                decoding="async" referrerPolicy="no-referrer" onLoad={() => setLoaded(true)} onError={() => setBroken(true)}
                className={`h-full w-full object-cover transition duration-500 group-hover:scale-[1.03] ${loaded ? 'opacity-100' : 'opacity-0'}`} />
            </>
          ) : (
            <div data-testid="image-fallback" className="relative h-full w-full overflow-hidden bg-surface2" role="img" aria-label={`${label} story`}>
              <img
                src={fallbackPhoto.url}
                alt={`${label} stock illustration`}
                width={1200}
                height={750}
                loading={index < 2 ? 'eager' : 'lazy'}
                decoding="async"
                referrerPolicy="no-referrer"
                className="h-full w-full object-cover transition duration-500 group-hover:scale-[1.03]"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent pointer-events-none" />
            </div>
          )}
        </div>
        <p className="absolute bottom-2 left-2 rounded-full bg-black/60 px-2 py-0.5 text-[11px] text-white backdrop-blur">
          {showImage && a.image!.attribution ? a.image!.attribution : fallbackPhoto.attribution}
        </p>
      </div>

      <div className={`flex flex-1 flex-col gap-3 p-5 ${lead ? 'lg:justify-center lg:p-8' : ''}`}>
        <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted">
          <Icon size={14} aria-hidden /> {label}
        </p>

        {a.aiHeadline ? (
          <>
            <h3 className={`font-semibold leading-snug tracking-tight ${lead ? 'text-2xl lg:text-3xl' : 'text-xl'}`}>
              <span className="mr-2 inline-block rounded-full border border-line px-2 py-0.5 align-middle text-[10px] font-semibold uppercase tracking-wider text-muted">AI rewrite</span>
              {a.aiHeadline}
            </h3>
            <p className="text-sm text-muted">
              <span className="mr-2 inline-block rounded-full border border-line px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider">Original</span>
              {a.originalTitle}
            </p>
          </>
        ) : (
          <h3 className={`font-semibold leading-snug tracking-tight ${lead ? 'text-2xl lg:text-3xl' : 'text-xl'}`}>
            <span className="mr-2 inline-block rounded-full border border-line px-2 py-0.5 align-middle text-[10px] font-semibold uppercase tracking-wider text-muted">Original</span>
            {a.originalTitle}
          </h3>
        )}

        {a.summary && <p className="line-clamp-3 text-sm text-muted">{a.summary}</p>}

        <div className="mt-auto flex flex-wrap items-center justify-between gap-3 pt-2">
          <p className="text-xs text-muted">
            {a.publisher} · <time dateTime={a.publishedAt}>{timeAgo(a.publishedAt)}</time>
            {a.coverage > 1 && <> · +{a.coverage - 1} {a.coverage === 2 ? 'source' : 'sources'}</>}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => onOpenSummary?.(a)}
              aria-label={`Open summary for ${a.originalTitle}`}
              className="press inline-flex min-h-11 items-center gap-1.5 rounded-full border border-line px-3.5 text-xs font-semibold hover:border-ink hover:bg-surface2 transition-all">
              <Sparkles size={14} className="text-amber-500" /> Summary
            </button>
            <a href={a.url} target="_blank" rel="noopener noreferrer"
              aria-label={`Read original: ${a.originalTitle} (opens in a new tab)`}
              className="press inline-flex min-h-11 items-center gap-1 rounded-full border border-line px-3.5 text-xs font-medium hover:bg-surface2">
              Read original <ArrowUpRight size={15} aria-hidden />
            </a>
          </div>
        </div>
      </div>
    </article>
  )
}
