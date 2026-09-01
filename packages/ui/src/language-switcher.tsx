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
  /** Accessible group label, translated by the caller (defaults to "Language"). */
  ariaLabel?: string
}

const OPTIONS: { value: AppLocale; label: string }[] = [
  { value: 'en', label: 'EN' },
  { value: 'he', label: 'HE' },
]

function LanguageSwitcher({ locale, onChange, disabled, className, ariaLabel = 'Language' }: LanguageSwitcherProps) {
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={cn(
        'inline-flex items-center rounded-md border border-input bg-background p-0.5 text-xs font-medium',
        className,
      )}
    >
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          disabled={disabled}
          aria-pressed={locale === opt.value}
          onClick={() => opt.value !== locale && onChange(opt.value)}
          className={cn(
            'rounded-[5px] px-2 py-1 transition-colors disabled:pointer-events-none disabled:opacity-50',
            locale === opt.value
              ? 'bg-primary text-primary-foreground'
              : 'text-muted-foreground hover:bg-accent hover:text-foreground',
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

export { LanguageSwitcher }
