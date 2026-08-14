import { describe, it, expect, vi } from 'vitest'
import { createReportsResource } from '@smartserve/api-client'
import type { Http } from '@smartserve/api-client'
import { dayRangeToIso } from '@/lib/report-utils'

function fakeHttp(): Http {
  return {
    get: vi.fn().mockResolvedValue({}),
    post: vi.fn(),
    postForm: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    del: vi.fn(),
    getBlob: vi.fn().mockResolvedValue({ blob: new Blob(), filename: 'report.csv' }),
  }
}

describe('reports resource query building', () => {
  it('URL-encodes the "+" in a UTC ISO offset so it is not read back as a space', () => {
    const http = fakeHttp()
    const reports = createReportsResource(http)
    const { start, end } = dayRangeToIso('2026-01-01', '2026-01-31')

    reports.sales('loc-1', { groupBy: 'category', start, end })

    const calledPath = (http.get as ReturnType<typeof vi.fn>).mock.calls[0][0] as string
    const query = calledPath.split('?')[1]
    const params = new URLSearchParams(query)
    // dayRangeToIso doesn't include a '+' offset (uses literal 'Z'), but this
    // guards against a regression to '+00:00'-style offsets breaking query parsing.
    expect(calledPath).not.toContain(' ')
    expect(params.get('start')).toBe(start)
    expect(params.get('end')).toBe(end)
    expect(params.get('group_by')).toBe('category')
  })

  it('omits itemId/categoryId from the export query when not provided', async () => {
    const http = fakeHttp()
    const reports = createReportsResource(http)

    await reports.exportCsv('loc-1', {
      reportType: 'closed-orders',
      start: '2026-01-01T00:00:00.000Z',
      end: '2026-01-31T23:59:59.999Z',
      status: 'paid',
    })

    const calledPath = (http.getBlob as ReturnType<typeof vi.fn>).mock.calls[0][0] as string
    const params = new URLSearchParams(calledPath.split('?')[1])
    expect(params.get('report_type')).toBe('closed-orders')
    expect(params.get('status')).toBe('paid')
    expect(params.has('item_id')).toBe(false)
    expect(params.has('category_id')).toBe(false)
  })

  it('passes item_id and category_id through for sales-by-server filtering', () => {
    const http = fakeHttp()
    const reports = createReportsResource(http)

    reports.salesByServer('loc-1', {
      start: '2026-01-01T00:00:00.000Z',
      end: '2026-01-31T23:59:59.999Z',
      itemId: 'item-1',
      categoryId: 'cat-1',
    })

    const calledPath = (http.get as ReturnType<typeof vi.fn>).mock.calls[0][0] as string
    const params = new URLSearchParams(calledPath.split('?')[1])
    expect(params.get('item_id')).toBe('item-1')
    expect(params.get('category_id')).toBe('cat-1')
  })
})
