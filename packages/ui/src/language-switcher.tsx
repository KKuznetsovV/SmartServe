'use client'

import * as React from 'react'
import { cn } from './utils'

export type AppLocale = 'he' | 'en'

export interface LanguageSwitcherProps {
  /** Currently active UI locale. */
  locale: AppLocale
  onChange: (locale: AppLocale) => void
  disabled?: boolean
  className?: string
  /** Accessible control label, translated by the caller (defaults to "Language"). */
  ariaLabel?: string
}

const LABELS: Record<AppLocale, string> = {
  en: 'EN',
  he: 'HE',
}

function LanguageSwitcher({ locale, onChange, disabled, className, ariaLabel = 'Language' }: LanguageSwitcherProps) {
  const next: AppLocale = locale === 'he' ? 'en' : 'he'

  return (
    <button
      type="button"
      disabled={disabled}
      aria-label={`${ariaLabel}: ${LABELS[locale]}`}
      title={LABELS[next]}
      onClick={() => onChange(next)}
      className={cn(
        'inline-flex h-8 min-w-8 items-center justify-center rounded-md border border-input bg-background px-2 text-xs font-medium text-foreground transition-colors hover:bg-accent disabled:pointer-events-none disabled:opacity-50',
        className,
      )}
    >
      {LABELS[locale]}
    </button>
  )
}

export { LanguageSwitcher }
