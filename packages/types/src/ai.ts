import { z } from 'zod'

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

// ─── AI Menu Import ───────────────────────────────────────────────────────────

export const MenuImportItemSchema = z.object({
  name: z.string(),
  nameHe: z.string().nullable().optional(),
  description: z.string().nullable().optional(),
  price: z.number().nullable().optional(),
  currency: z.string().nullable().optional(),
  category: z.string().nullable().optional(),
  printerTypes: z.array(z.enum(['kitchen', 'receipt', 'label'])).optional().default([]),
})
export type MenuImportItem = z.infer<typeof MenuImportItemSchema>

export const MenuImportTurnSchema = z.object({
  sessionId: z.string(),
  items: z.array(MenuImportItemSchema),
  message: z.string(),
  needsClarification: z.boolean(),
})
export type MenuImportTurn = z.infer<typeof MenuImportTurnSchema>

export const MenuImportApplyResponseSchema = z.object({
  categoriesCreated: z.number().int(),
  itemsCreated: z.number().int(),
  routesCreated: z.number().int(),
  unrouted: z.array(z.string()),
})
export type MenuImportApplyResponse = z.infer<typeof MenuImportApplyResponseSchema>
