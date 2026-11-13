import { TONES } from '../../config/categories'
import type { HumourMode } from '../../types'

export function TonePicker({ value, onChange }: { value: HumourMode; onChange: (m: HumourMode) => void }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-xs uppercase tracking-wider text-muted">Headline tone</span>
      <select value={value} onChange={(e) => onChange(e.target.value as HumourMode)}
        className="h-11 min-w-[200px] rounded-ctl border border-line bg-card px-3 text-ink">
        {TONES.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
      </select>
    </label>
  )
}
