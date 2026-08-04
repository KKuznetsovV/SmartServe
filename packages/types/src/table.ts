import { z } from 'zod'

export const TableSchema = z.object({
  id: z.string().uuid(),
  locationId: z.string().uuid(),
  name: z.string().min(1),
  capacity: z.number().int().min(1).default(4),
  section: z.string().optional(),
  posX: z.number().default(0),
  posY: z.number().default(0),
  active: z.boolean().default(true),
})
export type Table = z.infer<typeof TableSchema>
