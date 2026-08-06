import { z } from 'zod'

export const PaymentMethod = z.enum(['cash', 'card', 'tap', 'mobile', 'voucher'])
export type PaymentMethod = z.infer<typeof PaymentMethod>

export const PaymentStatus = z.enum(['pending', 'completed', 'failed', 'refunded'])
export type PaymentStatus = z.infer<typeof PaymentStatus>

export const PaymentSchema = z.object({
  id: z.string().uuid(),
  orderId: z.string().uuid(),
  method: PaymentMethod,
  amount: z.number().min(0),
  tipAmount: z.number().min(0).default(0),
  guestNumber: z.number().int().min(1).nullable().optional(),
  status: PaymentStatus.default('pending'),
  gatewayRef: z.string().optional(),
  createdAt: z.string().datetime(),
})
export type Payment = z.infer<typeof PaymentSchema>
