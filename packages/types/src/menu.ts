import { z } from 'zod'

export const MenuCategorySchema = z.object({
  id: z.string().uuid(),
  locationId: z.string().uuid(),
  parentId: z.string().uuid().nullable().optional(),
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
  sortOrder: z.number().int().default(0),
  active: z.boolean().default(true),
  inStock: z.boolean().default(true),
  defaultFireCourse: z.number().int().min(1).max(5).default(1),
  deletedAt: z.string().datetime().nullable().optional(),
  modifierGroups: z.array(ModifierGroupSchema).default([]),
})
export type MenuItem = z.infer<typeof MenuItemSchema>
