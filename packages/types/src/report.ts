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

export const ReportGroupBySchema = z.enum(['item', 'category', 'menu'])
export type ReportGroupBy = z.infer<typeof ReportGroupBySchema>

export const ClosedOrderStatusFilterSchema = z.enum(['paid', 'cancelled', 'other'])
export type ClosedOrderStatusFilter = z.infer<typeof ClosedOrderStatusFilterSchema>

export const ReportExportTypeSchema = z.enum(['sales', 'sales-by-server', 'closed-orders'])
export type ReportExportType = z.infer<typeof ReportExportTypeSchema>

export const SalesReportGroupSchema = z.object({
  groupId: z.string().nullable().optional(),
  groupLabel: z.string(),
  qty: z.number().int(),
  revenue: z.number(),
})
export type SalesReportGroup = z.infer<typeof SalesReportGroupSchema>

export const SalesReportSchema = z.object({
  groupBy: ReportGroupBySchema,
  start: z.string(),
  end: z.string(),
  rows: z.array(SalesReportGroupSchema),
  totalQty: z.number().int(),
  totalRevenue: z.number(),
})
export type SalesReport = z.infer<typeof SalesReportSchema>

export const ServerSalesSchema = z.object({
  serverId: z.string().nullable().optional(),
  serverName: z.string(),
  orderCount: z.number().int(),
  qty: z.number().int().nullable().optional(),
  revenue: z.number(),
})
export type ServerSales = z.infer<typeof ServerSalesSchema>

export const ServerSalesReportSchema = z.object({
  start: z.string(),
  end: z.string(),
  itemId: z.string().nullable().optional(),
  categoryId: z.string().nullable().optional(),
  rows: z.array(ServerSalesSchema),
})
export type ServerSalesReport = z.infer<typeof ServerSalesReportSchema>

export const ClosedOrderSchema = z.object({
  id: z.string(),
  status: z.string(),
  channel: z.string(),
  total: z.number(),
  createdBy: z.string().nullable().optional(),
  createdByName: z.string().nullable().optional(),
  createdAt: z.string(),
})
export type ClosedOrder = z.infer<typeof ClosedOrderSchema>

export const ClosedOrdersReportSchema = z.object({
  start: z.string(),
  end: z.string(),
  status: z.string().nullable().optional(),
  orders: z.array(ClosedOrderSchema),
})
export type ClosedOrdersReport = z.infer<typeof ClosedOrdersReportSchema>
