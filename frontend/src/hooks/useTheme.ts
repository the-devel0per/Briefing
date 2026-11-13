import { useCallback, useEffect, useState } from 'react'

export type Theme = 'light' | 'dark'
const read = (): Theme => (document.documentElement.classList.contains('dark') ? 'dark' : 'light')

/** index.html already applied the right class before paint; this hook only mirrors and toggles it. */
export function useTheme() {
  const [theme, setTheme] = useState<Theme>(read)

  const toggle = useCallback(() => {
    const next: Theme = read() === 'dark' ? 'light' : 'dark'
    const root = document.documentElement
    root.classList.add('theme-anim')
    root.classList.toggle('dark', next === 'dark')
    try { localStorage.setItem('theme', next) } catch { /* private mode: preference just won't persist */ }
    setTheme(next)
    window.setTimeout(() => root.classList.remove('theme-anim'), 350)
  }, [])

  // Follow the OS only while the user has not made an explicit choice.
  useEffect(() => {
    if (!window.matchMedia) return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = (e: MediaQueryListEvent) => {
      if (localStorage.getItem('theme')) return
      document.documentElement.classList.toggle('dark', e.matches)
      setTheme(e.matches ? 'dark' : 'light')
    }
    mq.addEventListener?.('change', onChange)
    return () => mq.removeEventListener?.('change', onChange)
  }, [])

  return { theme, toggle }
}
