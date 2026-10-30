import { z } from 'zod'

export const BusinessSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  taxId: z.string().optional(),
  country: z.string().default('IL'),
  currency: z.string().default('ILS'),
  vatRate: z.number().min(0).max(1).default(0.18),
  createdAt: z.string().datetime(),
})
export type Business = z.infer<typeof BusinessSchema>

export const LocationSchema = z.object({
  id: z.string().uuid(),
  businessId: z.string().uuid(),
  name: z.string().min(1),
  address: z.string().optional(),
  timezone: z.string().default('Asia/Jerusalem'),
  language: z.enum(['he', 'en']).default('he'),
  vatRate: z.number().min(0).max(1).nullable().optional(),
  active: z.boolean().default(true),
})
export type Location = z.infer<typeof LocationSchema>
