import { describe, it, expect, vi, afterEach } from 'vitest'
import { dayRangeToIso, downloadBlob } from '@/lib/report-utils'

describe('dayRangeToIso', () => {
  it('produces an inclusive UTC range spanning the full start and end days', () => {
    const { start, end } = dayRangeToIso('2026-03-01', '2026-03-15')
    expect(start).toBe('2026-03-01T00:00:00.000Z')
    expect(end).toBe('2026-03-15T23:59:59.999Z')
  })

  it('handles a single-day range', () => {
    const { start, end } = dayRangeToIso('2026-01-01', '2026-01-01')
    expect(start).toBe('2026-01-01T00:00:00.000Z')
    expect(end).toBe('2026-01-01T23:59:59.999Z')
  })
})

describe('downloadBlob', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('creates an object URL, clicks a temporary link, and revokes the URL', () => {
    const blob = new Blob(['a,b,c'], { type: 'text/csv' })
    const createObjectURL = vi.fn(() => 'blob:fake-url')
    const revokeObjectURL = vi.fn()
    URL.createObjectURL = createObjectURL
    URL.revokeObjectURL = revokeObjectURL

    const clickSpy = vi.fn()
    const originalCreateElement = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = originalCreateElement(tag)
      if (tag === 'a') el.click = clickSpy
      return el
    })

    downloadBlob(blob, 'sales-2026-01-01-to-2026-01-31.csv')

    expect(createObjectURL).toHaveBeenCalledWith(blob)
    expect(clickSpy).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:fake-url')
  })
})
