import type { ReportSummary } from '@smartserve/types'

import type { Http } from './client'

export function createReportsResource(http: Http) {
  return {
    summary: (locationId: string, period: 'today' | 'week' | 'month') =>
      http.get<ReportSummary>(`/locations/${locationId}/reports/summary?period=${period}`),
  }
}
