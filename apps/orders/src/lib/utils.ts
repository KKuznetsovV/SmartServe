import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { Order, OrderItem, Payment } from '@smartserve/types'

export { formatPrice } from '@smartserve/ui'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** An item's contribution to the bill: 0 when comped, otherwise qty*unitPrice less any
 * manual per-item discount. */
export function getItemLineTotal(item: OrderItem): number {
  return item.isComped ? 0 : Math.max(0, item.unitPrice * item.qty - item.discountAmount)
}

export interface GuestShare {
  guestNumber: number
  total: number
  paid: number
  remaining: number
}

/** Estimated per-guest share of the bill, proportional to each guest's tagged items.
 * Untagged/"shared" items are split evenly across every guest who has at least one
 * tagged item. Tax and any order-level discount aren't tracked per item, so they're
 * prorated using the same ratio. Returns [] when no item has been tagged with a guest. */
export function splitBillByGuest(order: Order, payments: Payment[]): GuestShare[] {
  const guestNumbers = Array.from(
    new Set(order.items.map((i) => i.guestNumber).filter((g): g is number => g != null)),
  ).sort((a, b) => a - b)
  if (guestNumbers.length === 0) return []

  const sharedSubtotal = order.items
    .filter((i) => i.guestNumber == null)
    .reduce((sum, i) => sum + getItemLineTotal(i), 0)
  const sharedPerGuest = sharedSubtotal / guestNumbers.length

  return guestNumbers.map((guestNumber) => {
    const guestSubtotal =
      order.items
        .filter((i) => i.guestNumber === guestNumber)
        .reduce((sum, i) => sum + getItemLineTotal(i), 0) + sharedPerGuest
    const ratio = order.subtotal > 0 ? guestSubtotal / order.subtotal : 0
    const total = Math.round(ratio * order.total * 100) / 100
    const paid = payments.filter((p) => p.guestNumber === guestNumber).reduce((sum, p) => sum + p.amount, 0)
    return { guestNumber, total, paid, remaining: Math.max(0, Math.round((total - paid) * 100) / 100) }
  })
}
