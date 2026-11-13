export function CardSkeleton() {
  return (
    <div className="overflow-hidden rounded-card border border-line bg-card" aria-hidden>
      <div className="skeleton aspect-[16/10] w-full" />
      <div className="space-y-3 p-5">
        <div className="skeleton h-3 w-24 rounded" />
        <div className="skeleton h-6 w-5/6 rounded" />
        <div className="skeleton h-4 w-2/3 rounded" />
      </div>
    </div>
  )
}

export function CategorySkeleton() {
  return (
    <div className="rounded-card border border-line bg-surface p-5 sm:p-6 shadow-sm" aria-hidden>
      <div className="flex items-center justify-between">
        <div className="skeleton h-5 w-32 rounded" />
        <div className="skeleton h-3.5 w-16 rounded" />
      </div>
      <div className="skeleton mt-2 h-3 w-56 rounded" />
      <div className="mt-4 grid gap-2.5 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="skeleton h-[58px] rounded-ctl" />
        ))}
      </div>
      <div className="mt-4 flex items-center justify-between border-t border-line/60 pt-3">
        <div className="skeleton h-10 w-36 rounded-ctl" />
        <div className="skeleton h-10 w-28 rounded-ctl" />
      </div>
    </div>
  )
}

export function FeedSkeleton() {
  return (
    <div role="status" aria-label="Loading your briefing" className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }, (_, i) => <CardSkeleton key={i} />)}
    </div>
  )
}
