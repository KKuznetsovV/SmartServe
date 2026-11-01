import type { DisplayOrder } from '@smartserve/types'

export function splitDisplayOrders(orders: DisplayOrder[]): {
  preparing: DisplayOrder[]
  ready: DisplayOrder[]
} {
  const preparing: DisplayOrder[] = []
  const ready: DisplayOrder[] = []
  for (const order of orders) {
    if (order.status === 'ready') ready.push(order)
    else preparing.push(order)
  }
  return { preparing, ready }
}

export function newlyReadyNumbers(
  previous: ReadonlySet<number>,
  nextReady: DisplayOrder[],
): number[] {
  const next = new Set(
    nextReady.map((order) => order.orderNumber).filter((n): n is number => n != null),
  )
  return [...next].filter((n) => !previous.has(n))
}
