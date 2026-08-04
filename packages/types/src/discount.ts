import { z } from 'zod'

export const DiscountType = z.enum(['percent', 'fixed'])
export type DiscountType = z.infer<typeof DiscountType>

export const DiscountSchema = z.object({
  id: z.string().uuid(),
  businessId: z.string().uuid(),
  code: z.string().min(1),
  name: z.string().min(1),
  type: DiscountType,
  value: z.number().min(0),
  minOrderAmount: z.number().min(0).default(0),
  active: z.boolean().default(true),
  expiresAt: z.string().datetime().optional(),
  createdAt: z.string().datetime(),
})
export type Discount = z.infer<typeof DiscountSchema>
