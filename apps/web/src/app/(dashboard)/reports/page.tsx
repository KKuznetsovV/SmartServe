'use client'

import { useMemo, useState } from 'react'
import { useReportSummary, useSalesReport, useSalesByServerReport, useClosedOrdersReport } from '@/hooks/use-reports'
import { useCategories, useMenuItems } from '@/hooks/use-menu'
import { useAuthStore } from '@/lib/auth-store'
import { dayRangeToIso } from '@/lib/report-utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import type { ReportPeriod } from '@/hooks/use-reports'
import type { ClosedOrderStatusFilter, ReportGroupBy } from '@smartserve/types'
import { AiReportQuery } from './components/ai-report-query'
import { ClosedOrdersReportView } from './components/closed-orders-report-view'
import { CsvExportButton } from './components/csv-export-button'
import { DateRangeFields } from './components/date-range-fields'
import { SalesReportView } from './components/sales-report-view'
import { ServerSalesReportView } from './components/server-sales-report-view'

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

type ReportTab = 'sales' | 'sales-by-server' | 'closed-orders'

const TABS: { value: ReportTab; label: string }[] = [
  { value: 'sales', label: 'Sales' },
  { value: 'sales-by-server', label: 'Sales by Server' },
  { value: 'closed-orders', label: 'Closed Orders' },
]

function isoDate(daysAgo: number): string {
  const d = new Date()
  d.setDate(d.getDate() - daysAgo)
  return d.toISOString().slice(0, 10)
}

function OverviewSection() {
  const locationId = useAuthStore((s) => s.activeLocationId)
  const [period, setPeriod] = useState<ReportPeriod>('today')
  const { data, isLoading } = useReportSummary(locationId, period)

  const channelEntries = Object.entries(data?.revenueByChannel ?? {}).sort((a, b) => b[1] - a[1])
  const statusEntries = Object.entries(data?.ordersByStatus ?? {})
  const maxChannelRevenue = Math.max(...channelEntries.map(([, v]) => v), 1)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Overview</h2>

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

function SalesTab({ locationId, startDate, endDate }: { locationId: string; startDate: string; endDate: string }) {
  const [groupBy, setGroupBy] = useState<ReportGroupBy>('item')
  const { start, end } = useMemo(() => dayRangeToIso(startDate, endDate), [startDate, endDate])
  const { data, isLoading } = useSalesReport(locationId, { groupBy, start, end })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <label className="text-sm font-medium text-muted-foreground">Group by</label>
          <Select value={groupBy} onChange={(e) => setGroupBy(e.target.value as ReportGroupBy)} className="w-40">
            <option value="item">Item</option>
            <option value="category">Category</option>
            <option value="menu">Whole menu</option>
          </Select>
        </div>
        <CsvExportButton locationId={locationId} params={{ reportType: 'sales', groupBy, start, end }} />
      </div>
      {isLoading && <Spinner />}
      {data && <SalesReportView report={data} />}
    </div>
  )
}

function SalesByServerTab({
  locationId,
  startDate,
  endDate,
}: {
  locationId: string
  startDate: string
  endDate: string
}) {
  const [categoryId, setCategoryId] = useState('')
  const [itemId, setItemId] = useState('')
  const { data: categories } = useCategories(locationId)
  const { data: items } = useMenuItems(categoryId || null, !!categoryId)
  const { start, end } = useMemo(() => dayRangeToIso(startDate, endDate), [startDate, endDate])
  const { data, isLoading } = useSalesByServerReport(locationId, {
    start,
    end,
    itemId: itemId || undefined,
    categoryId: itemId ? undefined : categoryId || undefined,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex gap-3">
          <div className="space-y-1">
            <label className="text-sm font-medium text-muted-foreground">Category</label>
            <Select
              value={categoryId}
              onChange={(e) => {
                setCategoryId(e.target.value)
                setItemId('')
              }}
              className="w-44"
            >
              <option value="">All categories</option>
              {categories?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium text-muted-foreground">Item</label>
            <Select value={itemId} onChange={(e) => setItemId(e.target.value)} disabled={!categoryId} className="w-44">
              <option value="">All items</option>
              {items?.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name}
                </option>
              ))}
            </Select>
          </div>
        </div>
        <CsvExportButton
          locationId={locationId}
          params={{
            reportType: 'sales-by-server',
            start,
            end,
            itemId: itemId || undefined,
            categoryId: itemId ? undefined : categoryId || undefined,
          }}
        />
      </div>
      {isLoading && <Spinner />}
      {data && <ServerSalesReportView report={data} />}
    </div>
  )
}

function ClosedOrdersTab({
  locationId,
  startDate,
  endDate,
}: {
  locationId: string
  startDate: string
  endDate: string
}) {
  const [status, setStatus] = useState<ClosedOrderStatusFilter | ''>('')
  const { start, end } = useMemo(() => dayRangeToIso(startDate, endDate), [startDate, endDate])
  const { data, isLoading } = useClosedOrdersReport(locationId, { start, end, status: status || undefined })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <label className="text-sm font-medium text-muted-foreground">Status</label>
          <Select
            value={status}
            onChange={(e) => setStatus(e.target.value as ClosedOrderStatusFilter | '')}
            className="w-40"
          >
            <option value="">All</option>
            <option value="paid">Paid</option>
            <option value="cancelled">Cancelled</option>
            <option value="other">Other</option>
          </Select>
        </div>
        <CsvExportButton
          locationId={locationId}
          params={{ reportType: 'closed-orders', start, end, status: status || undefined }}
        />
      </div>
      {isLoading && <Spinner />}
      {data && <ClosedOrdersReportView report={data} />}
    </div>
  )
}

function DetailedReportsSection({ locationId }: { locationId: string }) {
  const [tab, setTab] = useState<ReportTab>('sales')
  const [startDate, setStartDate] = useState(isoDate(6))
  const [endDate, setEndDate] = useState(isoDate(0))

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-lg font-semibold">Detailed Reports</h2>
        <DateRangeFields
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
        />
      </div>

      <div className="flex gap-1 rounded-lg border p-1 bg-muted w-fit">
        {TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value)}
            className={`px-3 py-1 rounded-md text-sm transition-colors ${
              tab === t.value ? 'bg-background shadow-sm font-medium' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <Card>
        <CardContent className="p-4">
          {tab === 'sales' && <SalesTab locationId={locationId} startDate={startDate} endDate={endDate} />}
          {tab === 'sales-by-server' && (
            <SalesByServerTab locationId={locationId} startDate={startDate} endDate={endDate} />
          )}
          {tab === 'closed-orders' && (
            <ClosedOrdersTab locationId={locationId} startDate={startDate} endDate={endDate} />
          )}
        </CardContent>
      </Card>

      <AiReportQuery />
    </div>
  )
}

export default function ReportsPage() {
  const locationId = useAuthStore((s) => s.activeLocationId)

  return (
    <div className="p-6 space-y-10">
      <h1 className="text-2xl font-bold">Reports</h1>
      <OverviewSection />
      {locationId && <DetailedReportsSection locationId={locationId} />}
    </div>
  )
}
