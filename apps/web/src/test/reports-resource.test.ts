import { describe, it, expect, vi } from 'vitest'
import { createReportsResource } from '@smartserve/api-client'
import type { Http } from '@smartserve/api-client'

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
  it('sends YYYY-MM-DD start_date and end_date, not UTC instants', () => {
    const http = fakeHttp()
    const reports = createReportsResource(http)

    reports.sales('loc-1', { groupBy: 'category', startDate: '2026-01-01', endDate: '2026-01-31' })

    const calledPath = (http.get as ReturnType<typeof vi.fn>).mock.calls[0][0] as string
    const params = new URLSearchParams(calledPath.split('?')[1])
    expect(params.get('start_date')).toBe('2026-01-01')
    expect(params.get('end_date')).toBe('2026-01-31')
    expect(params.get('group_by')).toBe('category')
    expect(params.has('start')).toBe(false)
  })

  it('omits itemId/categoryId from the export query when not provided', async () => {
    const http = fakeHttp()
    const reports = createReportsResource(http)

    await reports.exportCsv('loc-1', {
      reportType: 'closed-orders',
      startDate: '2026-01-01',
      endDate: '2026-01-31',
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
      startDate: '2026-01-01',
      endDate: '2026-01-31',
      itemId: 'item-1',
      categoryId: 'cat-1',
    })

    const calledPath = (http.get as ReturnType<typeof vi.fn>).mock.calls[0][0] as string
    const params = new URLSearchParams(calledPath.split('?')[1])
    expect(params.get('item_id')).toBe('item-1')
    expect(params.get('category_id')).toBe('cat-1')
  })
})
