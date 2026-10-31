import { describe, it, expect } from 'vitest'
import { localizedName, resolveAppLocale } from '@smartserve/ui'

describe('resolveAppLocale', () => {
  it('keeps he and en', () => {
    expect(resolveAppLocale('he')).toBe('he')
    expect(resolveAppLocale('en')).toBe('en')
  })

  it('falls back to he for missing or unknown cookies', () => {
    expect(resolveAppLocale(undefined)).toBe('he')
    expect(resolveAppLocale(null)).toBe('he')
    expect(resolveAppLocale('')).toBe('he')
    expect(resolveAppLocale('fr')).toBe('he')
    expect(resolveAppLocale('en-US')).toBe('he')
    expect(resolveAppLocale('../messages/he')).toBe('he')
  })
})

describe('localizedName', () => {
  const cola = { name: 'Cola', nameHe: 'קולה' }

  it('uses nameHe when the locale is Hebrew', () => {
    expect(localizedName(cola, 'he')).toBe('קולה')
  })

  it('keeps the default name in English and when nameHe is empty', () => {
    expect(localizedName(cola, 'en')).toBe('Cola')
    expect(localizedName({ name: 'Cola', nameHe: '  ' }, 'he')).toBe('Cola')
    expect(localizedName({ name: 'Cola' }, 'he')).toBe('Cola')
  })
})
