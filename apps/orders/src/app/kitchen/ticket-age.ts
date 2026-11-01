import type { OrderItem } from '@smartserve/types'

export function ticketSentAt(items: OrderItem[]): string | null {
  const times = items.map((i) => i.sentAt).filter((value): value is string => Boolean(value))
  if (times.length === 0) return null
  return times.reduce((earliest, value) => (value < earliest ? value : earliest))
}

export function ticketAgeMinutes(items: OrderItem[], now = Date.now()): number {
  const sentAt = ticketSentAt(items)
  if (!sentAt) return 0
  return Math.max(0, Math.floor((now - new Date(sentAt).getTime()) / 60_000))
}

export function ticketAgeClass(minutes: number): string {
  if (minutes >= 15) return 'text-red-400'
  if (minutes >= 10) return 'text-amber-400'
  return 'text-zinc-400'
}
