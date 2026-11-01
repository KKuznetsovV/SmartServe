import { describe, expect, it } from 'vitest'
import { newlyReadyNumbers, splitDisplayOrders } from '@/app/display/columns'
import type { DisplayOrder } from '@smartserve/types'

function order(orderNumber: number, status: DisplayOrder['status']): DisplayOrder {
  return { orderNumber, status, updatedAt: '2026-01-01T00:00:00.000Z' }
}

describe('customer display columns', () => {
  it('puts submitted and preparing in Preparing, ready in Ready', () => {
    const { preparing, ready } = splitDisplayOrders([
      order(12, 'submitted'),
      order(13, 'preparing'),
      order(14, 'ready'),
    ])
    expect(preparing.map((o) => o.orderNumber)).toEqual([12, 13])
    expect(ready.map((o) => o.orderNumber)).toEqual([14])
  })

  it('detects newly ready ticket numbers after the first snapshot', () => {
    expect(newlyReadyNumbers(new Set([10]), [order(10, 'ready'), order(11, 'ready')])).toEqual([11])
  })
})
