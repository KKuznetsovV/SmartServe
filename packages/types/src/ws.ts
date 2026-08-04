import { z } from 'zod'

export const WsEventType = z.enum([
  'order.created',
  'order.updated',
  'order.item_status_changed',
  'order.paid',
  'menu.item_toggled',
  'printer.status_changed',
])
export type WsEventType = z.infer<typeof WsEventType>

export const WsEventSchema = z.object({
  type: WsEventType,
  locationId: z.string().uuid(),
  payload: z.record(z.unknown()),
  timestamp: z.string().datetime(),
})
export type WsEvent = z.infer<typeof WsEventSchema>
