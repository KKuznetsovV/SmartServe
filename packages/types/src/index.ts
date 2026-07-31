import { z } from 'zod'

// ─── Business & Location ──────────────────────────────────────────────────────

export const BusinessSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  taxId: z.string().optional(),
  country: z.string().default('IL'),
  currency: z.string().default('ILS'),
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
  active: z.boolean().default(true),
})
export type Location = z.infer<typeof LocationSchema>

// ─── Auth & Users ─────────────────────────────────────────────────────────────

export const UserRole = z.enum(['owner', 'manager', 'cashier', 'waiter', 'kitchen'])
export type UserRole = z.infer<typeof UserRole>

export const UserSchema = z.object({
  id: z.string().uuid(),
  businessId: z.string().uuid(),
  email: z.string().email().optional(),
  name: z.string().min(1),
  role: UserRole,
  language: z.enum(['he', 'en']).default('he'),
  active: z.boolean().default(true),
})
export type User = z.infer<typeof UserSchema>

export const LoginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
})
export type Login = z.infer<typeof LoginSchema>

export const PinLoginSchema = z.object({
  locationId: z.string().uuid(),
  pin: z.string().length(4).regex(/^\d{4}$/),
})
export type PinLogin = z.infer<typeof PinLoginSchema>

export const TokenPairSchema = z.object({
  accessToken: z.string(),
  refreshToken: z.string(),
  expiresIn: z.number(),
})
export type TokenPair = z.infer<typeof TokenPairSchema>

// ─── Menu ─────────────────────────────────────────────────────────────────────

export const MenuCategorySchema = z.object({
  id: z.string().uuid(),
  locationId: z.string().uuid(),
  name: z.string().min(1),
  nameHe: z.string().optional(),
  sortOrder: z.number().int().default(0),
  active: z.boolean().default(true),
})
export type MenuCategory = z.infer<typeof MenuCategorySchema>

export const ModifierSchema = z.object({
  id: z.string().uuid(),
  groupId: z.string().uuid(),
  name: z.string().min(1),
  nameHe: z.string().optional(),
  priceDelta: z.number().default(0),
  active: z.boolean().default(true),
})
export type Modifier = z.infer<typeof ModifierSchema>

export const ModifierGroupSchema = z.object({
  id: z.string().uuid(),
  itemId: z.string().uuid(),
  name: z.string().min(1),
  nameHe: z.string().optional(),
  required: z.boolean().default(false),
  minSelect: z.number().int().min(0).default(0),
  maxSelect: z.number().int().min(1).default(1),
  modifiers: z.array(ModifierSchema).default([]),
})
export type ModifierGroup = z.infer<typeof ModifierGroupSchema>

export const MenuItemSchema = z.object({
  id: z.string().uuid(),
  categoryId: z.string().uuid(),
  name: z.string().min(1),
  nameHe: z.string().optional(),
  description: z.string().optional(),
  descriptionHe: z.string().optional(),
  price: z.number().min(0),
  taxRate: z.number().min(0).max(1).default(0.17), // 17% Israeli VAT
  imageUrl: z.string().url().optional(),
  preparationTimeMin: z.number().int().min(0).default(10),
  active: z.boolean().default(true),
  inStock: z.boolean().default(true),
  modifierGroups: z.array(ModifierGroupSchema).default([]),
})
export type MenuItem = z.infer<typeof MenuItemSchema>

// ─── Tables & Sections ───────────────────────────────────────────────────────

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

// ─── Orders ──────────────────────────────────────────────────────────────────

export const OrderChannel = z.enum(['dine_in', 'takeaway', 'delivery', 'online'])
export type OrderChannel = z.infer<typeof OrderChannel>

export const OrderStatus = z.enum([
  'open',
  'submitted',
  'preparing',
  'ready',
  'served',
  'paid',
  'cancelled',
])
export type OrderStatus = z.infer<typeof OrderStatus>

export const OrderItemStatus = z.enum(['pending', 'preparing', 'ready', 'served', 'cancelled'])
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
  items: z.array(OrderItemSchema).default([]),
  subtotal: z.number().min(0),
  taxAmount: z.number().min(0),
  total: z.number().min(0),
  notes: z.string().optional(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
})
export type Order = z.infer<typeof OrderSchema>

// ─── Payments ────────────────────────────────────────────────────────────────

export const PaymentMethod = z.enum(['cash', 'card', 'tap', 'mobile', 'voucher'])
export type PaymentMethod = z.infer<typeof PaymentMethod>

export const PaymentStatus = z.enum(['pending', 'completed', 'failed', 'refunded'])
export type PaymentStatus = z.infer<typeof PaymentStatus>

export const PaymentSchema = z.object({
  id: z.string().uuid(),
  orderId: z.string().uuid(),
  method: PaymentMethod,
  amount: z.number().min(0),
  status: PaymentStatus.default('pending'),
  gatewayRef: z.string().optional(),
  createdAt: z.string().datetime(),
})
export type Payment = z.infer<typeof PaymentSchema>

// ─── Printers ────────────────────────────────────────────────────────────────

export const PrinterType = z.enum(['receipt', 'kitchen', 'label'])
export type PrinterType = z.infer<typeof PrinterType>

export const PrinterSchema = z.object({
  id: z.string().uuid(),
  locationId: z.string().uuid(),
  name: z.string().min(1),
  type: PrinterType,
  ip: z.string().ip().optional(),
  port: z.number().int().default(9100),
  active: z.boolean().default(true),
})
export type Printer = z.infer<typeof PrinterSchema>

export const PrinterRouteSchema = z.object({
  printerId: z.string().uuid(),
  categoryId: z.string().uuid(),
})
export type PrinterRoute = z.infer<typeof PrinterRouteSchema>

// ─── AI Commands ─────────────────────────────────────────────────────────────

export const AiIntent = z.enum([
  'menu.create_item',
  'menu.update_item',
  'menu.bulk_price_change',
  'menu.toggle_availability',
  'menu.create_category',
  'menu.create_modifier_group',
  'printer.route',
  'printer.troubleshoot',
  'report.query',
  'staff.add_user',
  'staff.set_permissions',
  'inventory.set_threshold',
  'settings.business',
  'help.general',
])
export type AiIntent = z.infer<typeof AiIntent>

export const AiCommandRequestSchema = z.object({
  message: z.string().min(1).max(500),
  context: z.object({
    locationId: z.string().uuid(),
    currentScreen: z.string().optional(),
  }),
})
export type AiCommandRequest = z.infer<typeof AiCommandRequestSchema>

export const AiCommandResponseSchema = z.object({
  intent: AiIntent,
  confidence: z.number().min(0).max(1),
  params: z.record(z.unknown()),
  preview: z.string(),
  requiresConfirmation: z.boolean().default(true),
  executionId: z.string().uuid().optional(),
})
export type AiCommandResponse = z.infer<typeof AiCommandResponseSchema>

// ─── WebSocket Events ─────────────────────────────────────────────────────────

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

// ─── API Response wrapper ─────────────────────────────────────────────────────

export const ApiResponseSchema = <T extends z.ZodTypeAny>(dataSchema: T) =>
  z.object({
    data: dataSchema,
    meta: z
      .object({
        page: z.number().optional(),
        perPage: z.number().optional(),
        total: z.number().optional(),
      })
      .optional(),
  })

export const ApiErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.unknown()).optional(),
  }),
})
export type ApiError = z.infer<typeof ApiErrorSchema>

// ─── Reports ──────────────────────────────────────────────────────────────────

export const TopItemSchema = z.object({
  menuItemName: z.string(),
  qty: z.number().int(),
  revenue: z.number(),
})
export type TopItem = z.infer<typeof TopItemSchema>

export const ReportSummarySchema = z.object({
  period: z.enum(['today', 'week', 'month']),
  totalRevenue: z.number(),
  orderCount: z.number().int(),
  avgOrderValue: z.number(),
  revenueByChannel: z.record(z.number()),
  topItems: z.array(TopItemSchema),
  ordersByStatus: z.record(z.number().int()),
})
export type ReportSummary = z.infer<typeof ReportSummarySchema>

// ─── Discounts ────────────────────────────────────────────────────────────────

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

// ─── Shifts ───────────────────────────────────────────────────────────────────

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
