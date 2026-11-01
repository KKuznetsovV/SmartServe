import type { OrderItem, Printer, PrinterRoute } from '@smartserve/types'

export type KitchenStation = 'kitchen' | 'bar'

export function parseKitchenStation(value: string | null | undefined): KitchenStation {
  return value === 'bar' ? 'bar' : 'kitchen'
}

export function isBarPrinter(printer: Printer): boolean {
  return /bar/i.test(printer.name)
}

export function itemMatchesStation(
  item: Pick<OrderItem, 'menuItemId'>,
  station: KitchenStation,
  printers: Printer[],
  routes: PrinterRoute[],
): boolean {
  const printerById = new Map(printers.map((p) => [p.id, p]))
  const routed = routes
    .filter((r) => r.itemId === item.menuItemId)
    .map((r) => printerById.get(r.printerId))
    .filter((p): p is Printer => Boolean(p))

  if (routed.length === 0) return station === 'kitchen'

  const toBar = routed.some(isBarPrinter)
  const toKitchen = routed.some((p) => p.type === 'kitchen' || !isBarPrinter(p))
  if (station === 'bar') return toBar
  return toKitchen || !toBar
}
