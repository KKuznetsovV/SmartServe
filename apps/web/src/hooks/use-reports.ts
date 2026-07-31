'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'

export type ReportPeriod = 'today' | 'week' | 'month'

export function useReportSummary(locationId: string | null, period: ReportPeriod) {
  return useQuery({
    queryKey: ['reports', 'summary', locationId, period],
    queryFn: () => apiClient.reports.summary(locationId!, period),
    enabled: !!locationId,
    staleTime: 60_000,
  })
}
