import { z } from 'zod'

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
