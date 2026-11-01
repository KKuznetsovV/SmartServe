import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { OrderItemRow } from '@/app/(app)/orders/[orderId]/order-item-row'
import enMessages from '@/messages/en.json'
import heMessages from '@/messages/he.json'
import type { OrderItem } from '@smartserve/types'

vi.mock('@dnd-kit/sortable', () => ({
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: () => {},
    transform: null,
    transition: undefined,
    isDragging: false,
  }),
}))

vi.mock('@dnd-kit/utilities', () => ({
  CSS: { Transform: { toString: () => undefined } },
}))

const item: OrderItem = {
  id: '11111111-1111-1111-1111-111111111111',
  orderId: '22222222-2222-2222-2222-222222222222',
  menuItemId: '33333333-3333-3333-3333-333333333333',
  menuItemName: 'Cola',
  menuItemNameHe: 'קולה',
  qty: 1,
  unitPrice: 12,
  modifiers: [],
  status: 'pending',
  sortOrder: 0,
  fireCourse: 1,
  discountAmount: 0,
  isComped: false,
}

function renderRow(orderStatus: string) {
  return render(
    <NextIntlClientProvider locale="en" messages={enMessages}>
      <OrderItemRow item={item} orderStatus={orderStatus} draggable />
    </NextIntlClientProvider>,
  )
}

describe('OrderItemRow unsent status', () => {
  it('labels pending lines on an open ticket as not sent', () => {
    renderRow('open')
    expect(screen.getByText('Not sent')).toBeInTheDocument()
    expect(screen.queryByText('Pending')).not.toBeInTheDocument()
  })

  it('keeps pending after the ticket is sent to the kitchen', () => {
    renderRow('submitted')
    expect(screen.getByText('Pending')).toBeInTheDocument()
    expect(screen.queryByText('Not sent')).not.toBeInTheDocument()
  })

  it('shows the snapshotted Hebrew name on the ticket', () => {
    render(
      <NextIntlClientProvider locale="he" messages={heMessages}>
        <OrderItemRow
          item={{
            ...item,
            modifiers: [{ modifierId: '44444444-4444-4444-4444-444444444444', name: 'Large', nameHe: 'גדול', priceDelta: 0 }],
          }}
          orderStatus="open"
          draggable
        />
      </NextIntlClientProvider>,
    )
    expect(screen.getByText('1× קולה')).toBeInTheDocument()
    expect(screen.getByText('גדול')).toBeInTheDocument()
  })
})
