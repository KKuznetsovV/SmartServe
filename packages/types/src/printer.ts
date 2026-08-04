import { z } from 'zod'

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
  id: z.string().uuid(),
  printerId: z.string().uuid(),
  itemId: z.string().uuid(),
})
export type PrinterRoute = z.infer<typeof PrinterRouteSchema>
