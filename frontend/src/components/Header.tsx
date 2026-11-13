import type { Theme } from '../hooks/useTheme'
import { ThemeToggle } from './ThemeToggle'

export function Header({ theme, onToggleTheme }: { theme: Theme; onToggleTheme: () => void }) {
  const link = 'press inline-flex h-11 items-center rounded-ctl px-3 text-sm text-muted hover:text-ink'
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-bg/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-page items-center justify-between px-5 sm:px-8">
        <a href="#today" className="text-lg font-semibold tracking-tight">Briefing<span className="text-muted">.</span></a>
        <nav aria-label="Primary" className="flex items-center gap-1">
          <a className={link} href="#today">Today</a>
          <a className={link} href="#categories">Categories</a>
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        </nav>
      </div>
    </header>
  )
}
