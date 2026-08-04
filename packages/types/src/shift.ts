import { z } from 'zod'

export const ShiftSchema = z.object({
  id: z.string().uuid(),
  locationId: z.string().uuid(),
  openedBy: z.string().uuid(),
  closedBy: z.string().uuid().optional(),
  openedAt: z.string().datetime(),
  closedAt: z.string().datetime().optional(),
  openingCash: z.number().min(0),
  closingCash: z.number().min(0).optional(),
  status: z.enum(['open', 'closed']),
  notes: z.string().optional(),
})
export type Shift = z.infer<typeof ShiftSchema>
