'use client'

import * as React from 'react'
import { Sun, Moon } from 'lucide-react'
import { cn } from './utils'

export type ThemePreference = 'light' | 'dark'

const THEME_COOKIE = 'theme'

function applyResolvedTheme(preference: ThemePreference) {
  document.documentElement.classList.toggle('dark', preference === 'dark')
}

function readThemeCookie(): ThemePreference {
  if (typeof document === 'undefined') return 'light'
  const match = document.cookie.match(/(?:^|; )theme=([^;]*)/)
  const value = match ? decodeURIComponent(match[1]) : undefined
  return value === 'dark' ? 'dark' : 'light'
}

/**
 * Manages the light/dark preference on the client: applies the resolved `.dark`
 * class to `<html>` and calls `onPersist` (a server action writing the `theme`
 * cookie) whenever the user changes it. The initial value is read from the
 * `theme` cookie so it matches whatever the blocking no-flash script already
 * applied server-side.
 */
export function useThemeToggle(onPersist: (theme: ThemePreference) => void) {
  const [theme, setThemeState] = React.useState<ThemePreference>('light')

  React.useEffect(() => {
    setThemeState(readThemeCookie())
  }, [])

  React.useEffect(() => {
    applyResolvedTheme(theme)
  }, [theme])

  function setTheme(next: ThemePreference) {
    setThemeState(next)
    onPersist(next)
  }

  return { theme, setTheme }
}

export interface ThemeToggleProps {
  /** Currently selected preference (not the resolved light/dark value). */
  theme: ThemePreference
  onChange: (theme: ThemePreference) => void
  disabled?: boolean
  className?: string
  /** Accessible control label, translated by the caller (defaults to "Theme"). */
  ariaLabel?: string
  /** Per-option accessible labels, translated by the caller. */
  labels?: { light?: string; dark?: string }
}

const DEFAULT_LABELS: Required<NonNullable<ThemeToggleProps['labels']>> = {
  light: 'Light',
  dark: 'Dark',
}

function ThemeToggle({ theme, onChange, disabled, className, ariaLabel = 'Theme', labels }: ThemeToggleProps) {
  const resolvedLabels = { ...DEFAULT_LABELS, ...labels }
  const next = theme === 'dark' ? 'light' : 'dark'
  const Icon = theme === 'dark' ? Moon : Sun

  return (
    <button
      type="button"
      disabled={disabled}
      aria-label={`${ariaLabel}: ${resolvedLabels[theme]}`}
      title={resolvedLabels[next]}
      aria-pressed={theme === 'dark'}
      onClick={() => onChange(next)}
      className={cn(
        'inline-flex h-8 w-8 items-center justify-center rounded-md border border-input bg-background text-foreground transition-colors hover:bg-accent disabled:pointer-events-none disabled:opacity-50',
        className,
      )}
    >
      <Icon className="h-3.5 w-3.5" />
    </button>
  )
}

export { ThemeToggle, THEME_COOKIE }
