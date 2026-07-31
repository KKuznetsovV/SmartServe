'use client'

import { useState } from 'react'
import { useReportSummary, type ReportPeriod } from '@/hooks/use-reports'
import { useAuthStore } from '@/lib/auth-store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'

const PERIODS: { value: ReportPeriod; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'week', label: 'Last 7 days' },
  { value: 'month', label: 'Last 30 days' },
]

const CHANNEL_LABELS: Record<string, string> = {
  dine_in: 'Dine In',
  takeaway: 'Takeaway',
  delivery: 'Delivery',
  online: 'Online',
}

const STATUS_LABELS: Record<string, string> = {
  open: 'Open',
  submitted: 'Submitted',
  preparing: 'Preparing',
  ready: 'Ready',
  served: 'Served',
  paid: 'Paid',
  cancelled: 'Cancelled',
}

export default function ReportsPage() {
  const locationId = useAuthStore((s) => s.activeLocationId)
  const [period, setPeriod] = useState<ReportPeriod>('today')
  const { data, isLoading } = useReportSummary(locationId, period)

  const channelEntries = Object.entries(data?.revenueByChannel ?? {}).sort((a, b) => b[1] - a[1])
  const statusEntries = Object.entries(data?.ordersByStatus ?? {})
  const maxChannelRevenue = Math.max(...channelEntries.map(([, v]) => v), 1)

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Reports</h1>

        {/* Period selector */}
        <div className="flex gap-1 rounded-lg border p-1 bg-muted">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-3 py-1 rounded-md text-sm transition-colors ${
                period === p.value
                  ? 'bg-background shadow-sm font-medium'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <Spinner />}

      {data && (
        <>
          {/* KPI cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-muted-foreground">Revenue</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">₪{data.totalRevenue.toFixed(2)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-muted-foreground">Orders</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{data.orderCount}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-muted-foreground">Avg Order</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">₪{data.avgOrderValue.toFixed(2)}</p>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Revenue by channel */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Revenue by Channel</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {channelEntries.length === 0 && (
                  <p className="text-sm text-muted-foreground">No data</p>
                )}
                {channelEntries.map(([channel, revenue]) => (
                  <div key={channel}>
                    <div className="flex justify-between text-sm mb-1">
                      <span>{CHANNEL_LABELS[channel] ?? channel}</span>
                      <span className="font-medium">₪{revenue.toFixed(2)}</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{ width: `${(revenue / maxChannelRevenue) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Orders by status */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Orders by Status</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {statusEntries.length === 0 && (
                  <p className="text-sm text-muted-foreground">No data</p>
                )}
                {statusEntries.map(([status, count]) => (
                  <div key={status} className="flex justify-between text-sm">
                    <span className="capitalize">{STATUS_LABELS[status] ?? status}</span>
                    <span className="font-medium tabular-nums">{count}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Top items */}
          {data.topItems.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Top Items</CardTitle>
              </CardHeader>
              <CardContent>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left pb-2 font-medium text-muted-foreground">Item</th>
                      <th className="text-right pb-2 font-medium text-muted-foreground">Qty</th>
                      <th className="text-right pb-2 font-medium text-muted-foreground">Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.topItems.map((item, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-2">{item.menuItemName}</td>
                        <td className="py-2 text-right tabular-nums">{item.qty}</td>
                        <td className="py-2 text-right tabular-nums font-medium">
                          ₪{item.revenue.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
