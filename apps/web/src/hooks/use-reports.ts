'use client'

import { useMutation } from '@tanstack/react-query'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { downloadBlob } from '@/lib/report-utils'
import type {
  ClosedOrdersReportParams,
  ExportReportParams,
  SalesReportParams,
  ServerSalesReportParams,
} from '@smartserve/api-client'

export type ReportPeriod = 'today' | 'week' | 'month'

export function useReportSummary(locationId: string | null, period: ReportPeriod) {
  return useQuery({
    queryKey: ['reports', 'summary', locationId, period],
    queryFn: () => apiClient.reports.summary(locationId!, period),
    enabled: !!locationId,
    staleTime: 60_000,
  })
}

export function useSalesReport(locationId: string | null, params: SalesReportParams | null) {
  return useQuery({
    queryKey: ['reports', 'sales', locationId, params],
    queryFn: () => apiClient.reports.sales(locationId!, params!),
    enabled: !!locationId && !!params,
  })
}

export function useSalesByServerReport(locationId: string | null, params: ServerSalesReportParams | null) {
  return useQuery({
    queryKey: ['reports', 'sales-by-server', locationId, params],
    queryFn: () => apiClient.reports.salesByServer(locationId!, params!),
    enabled: !!locationId && !!params,
  })
}

export function useClosedOrdersReport(locationId: string | null, params: ClosedOrdersReportParams | null) {
  return useQuery({
    queryKey: ['reports', 'closed-orders', locationId, params],
    queryFn: () => apiClient.reports.closedOrders(locationId!, params!),
    enabled: !!locationId && !!params,
  })
}

export function useExportReportCsv() {
  return useMutation({
    mutationFn: async ({ locationId, params }: { locationId: string; params: ExportReportParams }) => {
      const { blob, filename } = await apiClient.reports.exportCsv(locationId, params)
      downloadBlob(blob, filename ?? `${params.reportType}.csv`)
    },
  })
}
