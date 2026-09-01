'use client'

import * as React from 'react'
import { Sun, Moon, Monitor } from 'lucide-react'
import { cn } from './utils'

export type ThemePreference = 'light' | 'dark' | 'system'

const THEME_COOKIE = 'theme'

function isDarkPreferred(preference: ThemePreference): boolean {
  if (preference === 'dark') return true
  if (preference === 'light') return false
  return typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches
}

function applyResolvedTheme(preference: ThemePreference) {
  document.documentElement.classList.toggle('dark', isDarkPreferred(preference))
}

function readThemeCookie(): ThemePreference {
  if (typeof document === 'undefined') return 'system'
  const match = document.cookie.match(/(?:^|; )theme=([^;]*)/)
  const value = match ? decodeURIComponent(match[1]) : undefined
  return value === 'light' || value === 'dark' ? value : 'system'
}

/**
 * Manages the light/dark/system preference on the client: applies the resolved
 * `.dark` class to `<html>`, keeps it in sync with OS changes while "system" is
 * selected, and calls `onPersist` (a server action writing the `theme` cookie)
 * whenever the user changes it. The initial value is read from the `theme` cookie
 * so it matches whatever the blocking no-flash script already applied server-side.
 */
export function useThemeToggle(onPersist: (theme: ThemePreference) => void) {
  const [theme, setThemeState] = React.useState<ThemePreference>('system')

  React.useEffect(() => {
    setThemeState(readThemeCookie())
  }, [])

  React.useEffect(() => {
    applyResolvedTheme(theme)
    if (theme !== 'system') return
    const mql = window.matchMedia('(prefers-color-scheme: dark)')
    const listener = () => applyResolvedTheme('system')
    mql.addEventListener('change', listener)
    return () => mql.removeEventListener('change', listener)
  }, [theme])

  function setTheme(next: ThemePreference) {
    setThemeState(next)
    onPersist(next)
  }

  return { theme, setTheme }
}

/**
 * Static markup for a blocking inline script placed at the start of `<body>`.
 * It applies the resolved theme before first paint (based on the server-read
 * cookie value passed in), so there is no flash of the wrong theme while React
 * hydrates. Contains no user input — safe for `dangerouslySetInnerHTML`.
 */
export function getNoFlashThemeScript(serverTheme: ThemePreference): string {
  return `(function(){try{var v=${JSON.stringify(serverTheme)};var d=v==='dark'||(v==='system'&&window.matchMedia('(prefers-color-scheme: dark)').matches);if(d)document.documentElement.classList.add('dark');}catch(e){}})();`
}

export interface ThemeToggleProps {
  /** Currently selected preference (not the resolved light/dark value). */
  theme: ThemePreference
  onChange: (theme: ThemePreference) => void
  disabled?: boolean
  className?: string
  /** Accessible group label, translated by the caller (defaults to "Theme"). */
  ariaLabel?: string
  /** Per-option accessible labels, translated by the caller. */
  labels?: { light?: string; dark?: string; system?: string }
}

const OPTIONS: { value: ThemePreference; Icon: typeof Sun }[] = [
  { value: 'light', Icon: Sun },
  { value: 'dark', Icon: Moon },
  { value: 'system', Icon: Monitor },
]

const DEFAULT_LABELS: Required<NonNullable<ThemeToggleProps['labels']>> = {
  light: 'Light',
  dark: 'Dark',
  system: 'System',
}

function ThemeToggle({ theme, onChange, disabled, className, ariaLabel = 'Theme', labels }: ThemeToggleProps) {
  const resolvedLabels = { ...DEFAULT_LABELS, ...labels }

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={cn(
        'inline-flex items-center rounded-md border border-input bg-background p-0.5',
        className,
      )}
    >
      {OPTIONS.map(({ value, Icon }) => (
        <button
          key={value}
          type="button"
          disabled={disabled}
          aria-pressed={theme === value}
          aria-label={resolvedLabels[value]}
          title={resolvedLabels[value]}
          onClick={() => value !== theme && onChange(value)}
          className={cn(
            'rounded-[5px] p-1.5 transition-colors disabled:pointer-events-none disabled:opacity-50',
            theme === value
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-accent hover:text-foreground',
          )}
        >
          <Icon className="h-3.5 w-3.5" />
        </button>
      ))}
    </div>
  )
}

export { ThemeToggle, THEME_COOKIE }
