import { describe, it, expect } from 'vitest'

const OPEN_FLOOR_STATUSES = ['open', 'submitted', 'preparing', 'ready', 'served', 'split'] as const

function floorStateForOrder(status: string | null): string {
  if (status == null) return 'free'
  if (status === 'open') return 'seated'
  if (status === 'submitted' || status === 'preparing') return 'ordered'
  if (status === 'ready') return 'food_ready'
  if (status === 'served' || status === 'split') return 'waiting_to_pay'
  return 'seated'
}

describe('floor_state_for_order', () => {
  it('maps open tickets onto the floor colours', () => {
    expect(floorStateForOrder(null)).toBe('free')
    expect(floorStateForOrder('open')).toBe('seated')
    expect(floorStateForOrder('submitted')).toBe('ordered')
    expect(floorStateForOrder('ready')).toBe('food_ready')
    expect(floorStateForOrder('served')).toBe('waiting_to_pay')
    expect(OPEN_FLOOR_STATUSES).toContain('split')
  })
})
