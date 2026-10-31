import type {
  ClosedOrderStatusFilter,
  ClosedOrdersReport,
  ReportExportType,
  ReportGroupBy,
  ReportSummary,
  SalesReport,
  ServerSalesReport,
} from '@smartserve/types'

import type { Http } from './client'

export interface SalesReportParams {
  groupBy: ReportGroupBy
  startDate: string
  endDate: string
}

export interface ServerSalesReportParams {
  startDate: string
  endDate: string
  itemId?: string
  categoryId?: string
}

export interface ClosedOrdersReportParams {
  startDate: string
  endDate: string
  status?: ClosedOrderStatusFilter
}

export interface ExportReportParams {
  reportType: ReportExportType
  startDate: string
  endDate: string
  groupBy?: ReportGroupBy
  itemId?: string
  categoryId?: string
  status?: ClosedOrderStatusFilter
}

function toQuery(params: Record<string, string | undefined>): string {
  const usp = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) usp.set(key, value)
  }
  return usp.toString()
}

export function createReportsResource(http: Http) {
  return {
    summary: (locationId: string, period: 'today' | 'week' | 'month') =>
      http.get<ReportSummary>(`/locations/${locationId}/reports/summary?period=${period}`),

    sales: (locationId: string, params: SalesReportParams) =>
      http.get<SalesReport>(
        `/locations/${locationId}/reports/sales?${toQuery({
          group_by: params.groupBy,
          start_date: params.startDate,
          end_date: params.endDate,
        })}`,
      ),

    salesByServer: (locationId: string, params: ServerSalesReportParams) =>
      http.get<ServerSalesReport>(
        `/locations/${locationId}/reports/sales-by-server?${toQuery({
          start_date: params.startDate,
          end_date: params.endDate,
          item_id: params.itemId,
          category_id: params.categoryId,
        })}`,
      ),

    closedOrders: (locationId: string, params: ClosedOrdersReportParams) =>
      http.get<ClosedOrdersReport>(
        `/locations/${locationId}/reports/closed-orders?${toQuery({
          start_date: params.startDate,
          end_date: params.endDate,
          status: params.status,
        })}`,
      ),

    exportCsv: (locationId: string, params: ExportReportParams) =>
      http.getBlob(
        `/locations/${locationId}/reports/export?${toQuery({
          report_type: params.reportType,
          start_date: params.startDate,
          end_date: params.endDate,
          group_by: params.groupBy,
          item_id: params.itemId,
          category_id: params.categoryId,
          status: params.status,
        })}`,
      ),
  }
}
