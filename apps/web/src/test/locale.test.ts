import { describe, it, expect } from 'vitest'
import { resolveAppLocale } from '@smartserve/ui'

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
