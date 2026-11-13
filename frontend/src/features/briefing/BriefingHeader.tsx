import type { ReactNode } from 'react'
import type { Briefing } from '../../types'
import { formatDay, timeAgo } from '../../utils/time'

export function BriefingHeader({
  briefing,
  count,
  children,
}: {
  briefing: Briefing | null
  count: number
  children?: ReactNode
}) {
  return (
    <section id="today" className="pb-8 pt-8 sm:pt-12">
      <div className="grid items-start gap-8 lg:grid-cols-12">
        <div className="lg:col-span-5">
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">Your Daily Briefing</h1>
          <p className="mt-3 text-lg text-muted">Ten important stories. Everything worth knowing today.</p>
          {briefing && (
            <dl className="mt-8 flex flex-wrap gap-x-8 gap-y-3 text-sm">
              <Meta label="Date" value={formatDay(briefing.date)} />
              <Meta label="Updated" value={briefing.lastUpdated ? timeAgo(briefing.lastUpdated) : 'waiting for first update'} />
              <Meta label="Stories" value={String(count)} />
              <Meta label="Categories" value={`${briefing.activeCategories.length} of 4 active`} />
            </dl>
          )}
        </div>
        {children && (
          <div className="lg:col-span-7">
            {children}
          </div>
        )}
      </div>
    </section>
  )
}

const Meta = ({ label, value }: { label: string; value: string }) => (
  <div><dt className="text-xs uppercase tracking-wider text-muted">{label}</dt><dd className="font-medium">{value}</dd></div>
)
