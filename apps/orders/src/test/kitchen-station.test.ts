import { describe, it, expect } from 'vitest'
import { itemMatchesStation, parseKitchenStation } from '@/app/kitchen/station'
import { ticketAgeClass, ticketAgeMinutes } from '@/app/kitchen/ticket-age'
import type { OrderItem, Printer, PrinterRoute } from '@smartserve/types'

const kitchenPrinter: Printer = {
  id: '11111111-1111-1111-1111-111111111111',
  locationId: '22222222-2222-2222-2222-222222222222',
  name: 'Kitchen',
  type: 'kitchen',
  port: 9100,
  active: true,
}
const barPrinter: Printer = {
  ...kitchenPrinter,
  id: '33333333-3333-3333-3333-333333333333',
  name: 'Bar',
  type: 'receipt',
}

describe('kitchen station filter', () => {
  it('keeps drinks off the kitchen screen when they route to the bar', () => {
    const routes: PrinterRoute[] = [
      {
        id: '44444444-4444-4444-4444-444444444444',
        printerId: barPrinter.id,
        itemId: '55555555-5555-5555-5555-555555555555',
      },
    ]
    const cola = { menuItemId: '55555555-5555-5555-5555-555555555555' }
    expect(itemMatchesStation(cola, 'kitchen', [kitchenPrinter, barPrinter], routes)).toBe(false)
    expect(itemMatchesStation(cola, 'bar', [kitchenPrinter, barPrinter], routes)).toBe(true)
  })

  it('defaults unknown station query values to kitchen', () => {
    expect(parseKitchenStation('bar')).toBe('bar')
    expect(parseKitchenStation('nope')).toBe('kitchen')
  })
})

describe('ticket age', () => {
  it('turns amber at 10 minutes and red at 15', () => {
    expect(ticketAgeClass(9)).toContain('zinc')
    expect(ticketAgeClass(10)).toContain('amber')
    expect(ticketAgeClass(15)).toContain('red')
  })

  it('ages from the earliest sentAt', () => {
    const now = Date.parse('2026-01-01T00:15:00.000Z')
    const items = [
      { sentAt: '2026-01-01T00:00:00.000Z' },
      { sentAt: '2026-01-01T00:10:00.000Z' },
    ] as OrderItem[]
    expect(ticketAgeMinutes(items, now)).toBe(15)
  })
})
