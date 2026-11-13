import { useState } from 'react'
import { applySyncCode, getSyncCode } from '../../services/session'

/** No accounts: your settings follow a secret sync code. Paste it on another device to continue there. */
export function SyncCode({ onSynced }: { onSynced: () => void }) {
  const [code, setCode] = useState('')
  const [msg, setMsg] = useState<string | null>(null)

  const copy = async () => {
    try { await navigator.clipboard.writeText(getSyncCode() ?? ''); setMsg('Sync code copied. Keep it private.') }
    catch { setMsg('Could not copy automatically.') }
  }
  const apply = () => {
    try { applySyncCode(code); setCode(''); setMsg('Synced.'); onSynced() }
    catch (e) { setMsg(e instanceof Error ? e.message : 'Invalid code') }
  }
  const btn = 'press h-11 rounded-ctl border border-line px-4 text-sm hover:bg-surface2'

  return (
    <details className="text-sm">
      <summary className="inline-flex h-11 cursor-pointer items-center text-muted hover:text-ink">Use on another device</summary>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <button type="button" className={btn} onClick={copy}>Copy sync code</button>
        <input aria-label="Paste a sync code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="Paste code"
          className="h-11 w-40 rounded-ctl border border-line bg-card px-3" />
        <button type="button" className={btn} onClick={apply} disabled={!code}>Apply</button>
      </div>
      <p role="status" className="mt-2 text-xs text-muted">{msg}</p>
    </details>
  )
}
