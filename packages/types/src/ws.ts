import { z } from 'zod'

export const WsEventType = z.enum([
  'order.created',
  'order.updated',
  'order.item_status_changed',
  'order.item_fired',
  'order.paid',
  'menu.item_toggled',
  'menu.item_updated',
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

export const WsTicketSchema = z.object({
  ticket: z.string().min(1),
  expiresIn: z.number().int(),
})
export type WsTicket = z.infer<typeof WsTicketSchema>
