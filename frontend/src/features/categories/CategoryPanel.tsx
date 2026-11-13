import { Check } from 'lucide-react'
import { CATEGORIES } from '../../config/categories'
import type { CategoryId, Preferences } from '../../types'
import { TonePicker } from '../preferences/TonePicker'

interface Props {
  preferences: Preferences
  counts: Record<CategoryId, number>
  onChange: (next: Preferences) => void
  onSynced?: () => void
}

export function CategoryPanel({ preferences, counts, onChange }: Props) {
  const muted = new Set(preferences.mutedCategories)
  const activeCount = CATEGORIES.length - muted.size

  const toggle = (id: CategoryId) => {
    const next = new Set(muted)
    if (next.has(id)) next.delete(id)
    else if (activeCount > 1) next.add(id) // Hick's law + safety: at least one category stays on
    else return
    onChange({ ...preferences, mutedCategories: [...next] })
  }

  return (
    <section id="categories" aria-labelledby="cat-h" className="rounded-card border border-line bg-surface p-5 sm:p-6 shadow-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="cat-h" className="text-lg font-semibold tracking-tight">Your categories</h2>
        <span className="text-xs text-muted">{activeCount} of {CATEGORIES.length} active</span>
      </div>
      <p className="mt-1 text-xs text-muted">Mute what you don’t want. Slots reallocate to the best stories.</p>
      <ul className="mt-4 grid gap-2.5 sm:grid-cols-2">
        {CATEGORIES.map(({ id, label, Icon }) => {
          const on = !muted.has(id)
          const locked = on && activeCount === 1
          return (
            <li key={id}>
              <button type="button" role="switch" aria-checked={on} disabled={locked}
                aria-label={`${label}, ${counts[id] ?? 0} stories available`}
                title={locked ? 'At least one category must stay on' : undefined}
                onClick={() => toggle(id)}
                className={`press flex min-h-[58px] w-full items-center gap-2.5 rounded-ctl border px-3.5 py-2.5 text-left transition-all duration-200 disabled:cursor-not-allowed ${on ? 'border-ink bg-card' : 'border-line bg-transparent text-muted opacity-60'}`}>
                <Icon size={18} aria-hidden className="shrink-0" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-medium sm:text-sm">{label}</span>
                  <span className="block text-[11px] text-muted">{counts[id] ?? 0} available</span>
                </span>
                <span aria-hidden className={`grid h-4.5 w-4.5 shrink-0 place-items-center rounded-full border ${on ? 'border-ink bg-ink text-bg' : 'border-line'}`}>
                  {on && <Check size={11} />}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-line/60 pt-3">
        <TonePicker value={preferences.humourMode} onChange={(humourMode) => onChange({ ...preferences, humourMode })} />
      </div>
    </section>
  )
}
