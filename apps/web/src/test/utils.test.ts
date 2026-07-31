import { describe, it, expect } from 'vitest'
import { cn, formatPrice } from '@/lib/utils'

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('a', 'b')).toBe('a b')
  })

  it('resolves tailwind conflicts, keeping the last value', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4')
  })

  it('ignores falsy values', () => {
    expect(cn('a', false, null, undefined, 'b')).toBe('a b')
  })
})

describe('formatPrice', () => {
  it('formats ILS amounts', () => {
    const result = formatPrice(100, 'ILS')
    expect(result).toContain('100')
    expect(result).toMatch(/[₪]|ILS/)
  })

  it('formats USD amounts', () => {
    const result = formatPrice(9.99, 'USD')
    expect(result).toContain('9.99')
    expect(result).toMatch(/[$]|USD/)
  })

  it('defaults to ILS currency', () => {
    const withDefault = formatPrice(50)
    const withExplicit = formatPrice(50, 'ILS')
    expect(withDefault).toBe(withExplicit)
  })
})
