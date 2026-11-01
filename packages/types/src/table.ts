import { z } from 'zod'

export const TableFloorState = z.enum(['free', 'seated', 'ordered', 'food_ready', 'waiting_to_pay'])
export type TableFloorState = z.infer<typeof TableFloorState>

export const TableOpenOrderSchema = z.object({
  id: z.string().uuid(),
  status: z.string(),
  guestCount: z.number().int().nullable().optional(),
  seatedSince: z.string().datetime(),
  total: z.number(),
})
export type TableOpenOrder = z.infer<typeof TableOpenOrderSchema>

export const TableSchema = z.object({
  id: z.string().uuid(),
  locationId: z.string().uuid(),
  name: z.string().min(1),
  capacity: z.number().int().min(1).default(4),
  section: z.string().optional(),
  posX: z.number().default(0),
  posY: z.number().default(0),
  active: z.boolean().default(true),
  floorState: TableFloorState.optional(),
  openOrder: TableOpenOrderSchema.nullable().optional(),
})
export type Table = z.infer<typeof TableSchema>
