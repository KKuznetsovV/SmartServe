import { describe, it, expect } from 'vitest'
import { ordersAppUrl } from '@/lib/orders-app-url'

describe('ordersAppUrl', () => {
  it('points order and table routes at the orders app origin', () => {
    expect(ordersAppUrl('/orders')).toBe('http://localhost:3001/orders')
    expect(ordersAppUrl('/tables')).toBe('http://localhost:3001/tables')
    expect(ordersAppUrl('/orders?status=ready')).toBe('http://localhost:3001/orders?status=ready')
    expect(ordersAppUrl('/orders/abc')).toBe('http://localhost:3001/orders/abc')
  })
})
