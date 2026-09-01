import { z } from 'zod'

export const OrderChannel = z.enum(['dine_in', 'takeaway', 'delivery', 'online'])
export type OrderChannel = z.infer<typeof OrderChannel>

export const OrderStatus = z.enum([
  'open',
  'submitted',
  'preparing',
  'ready',
  'served',
  'paid',
  'split',
  'cancelled',
])
export type OrderStatus = z.infer<typeof OrderStatus>

export const OrderItemStatus = z.enum(['held', 'pending', 'preparing', 'ready', 'served', 'cancelled'])
export type OrderItemStatus = z.infer<typeof OrderItemStatus>

export const OrderItemSchema = z.object({
  id: z.string().uuid(),
  orderId: z.string().uuid(),
  menuItemId: z.string().uuid(),
  menuItemName: z.string(),
  qty: z.number().int().min(1),
  unitPrice: z.number().min(0),
  modifiers: z
    .array(
      z.object({
        modifierId: z.string().uuid(),
        name: z.string(),
        priceDelta: z.number(),
      }),
    )
    .default([]),
  notes: z.string().optional(),
  status: OrderItemStatus.default('pending'),
  sortOrder: z.number().int().default(0),
  fireCourse: z.number().int().min(1).max(5).default(1),
  guestNumber: z.number().int().min(1).nullable().optional(),
  discountType: z.enum(['percent', 'fixed']).nullable().optional(),
  discountValue: z.number().nullable().optional(),
  discountAmount: z.number().min(0).default(0),
  isComped: z.boolean().default(false),
  compedBy: z.string().uuid().nullable().optional(),
})
export type OrderItem = z.infer<typeof OrderItemSchema>

export const OrderSchema = z.object({
  id: z.string().uuid(),
  locationId: z.string().uuid(),
  tableId: z.string().uuid().optional(),
  tableName: z.string().optional(),
  discountId: z.string().uuid().optional(),
  discountAmount: z.number().min(0).default(0),
  channel: OrderChannel.default('dine_in'),
  status: OrderStatus.default('open'),
  guestCount: z.number().int().min(1).optional(),
  firedCourses: z.array(z.number().int()).default([]),
  items: z.array(OrderItemSchema).default([]),
  subtotal: z.number().min(0),
  taxAmount: z.number().min(0),
  total: z.number().min(0),
  notes: z.string().optional(),
  createdBy: z.string().uuid().nullable().optional(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
})
export type Order = z.infer<typeof OrderSchema>
