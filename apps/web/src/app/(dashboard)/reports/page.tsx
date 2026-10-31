'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { useReportSummary, useSalesReport, useSalesByServerReport, useClosedOrdersReport } from '@/hooks/use-reports'
import { useCategories, useMenuItems } from '@/hooks/use-menu'
import { useAuthStore } from '@/lib/auth-store'
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

const PERIODS: ReportPeriod[] = ['today', 'week', 'month']

type ReportTab = 'sales' | 'sales-by-server' | 'closed-orders'

const TABS: ReportTab[] = ['sales', 'sales-by-server', 'closed-orders']
const TAB_KEY: Record<ReportTab, 'tab_sales' | 'tab_salesByServer' | 'tab_closedOrders'> = {
  sales: 'tab_sales',
  'sales-by-server': 'tab_salesByServer',
  'closed-orders': 'tab_closedOrders',
}

function isoDate(daysAgo: number): string {
  const d = new Date()
  d.setDate(d.getDate() - daysAgo)
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function OverviewSection() {
  const t = useTranslations('reports')
  const tOrders = useTranslations('orders')
  const locationId = useAuthStore((s) => s.activeLocationId)
  const [period, setPeriod] = useState<ReportPeriod>('today')
  const { data, isLoading } = useReportSummary(locationId, period)

  const channelEntries = Object.entries(data?.revenueByChannel ?? {}).sort((a, b) => b[1] - a[1])
  const statusEntries = Object.entries(data?.ordersByStatus ?? {})
  const maxChannelRevenue = Math.max(...channelEntries.map(([, v]) => v), 1)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{t('overview')}</h2>

        {/* Period selector */}
        <div className="flex gap-1 rounded-lg border p-1 bg-muted">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1 rounded-md text-sm transition-colors ${
                period === p
                  ? 'bg-background shadow-sm font-medium'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {t(`period_${p}`)}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <Spinner />}

      {data && (
        <>
          {/* KPI cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-muted-foreground">{t('revenue')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">₪{data.totalRevenue.toFixed(2)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-muted-foreground">{t('vatCollected')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">₪{(data.vatCollected ?? 0).toFixed(2)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-muted-foreground">{t('netRevenue')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">₪{(data.netRevenue ?? 0).toFixed(2)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-muted-foreground">{t('orders')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{data.orderCount}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-muted-foreground">{t('avgOrder')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">₪{data.avgOrderValue.toFixed(2)}</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-1">
                <CardTitle className="text-sm font-medium text-muted-foreground">{t('openOrders')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{data.openOrderCount ?? 0}</p>
                <p className="text-sm text-muted-foreground tabular-nums">
                  ₪{(data.openOrderValue ?? 0).toFixed(2)}
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Revenue by channel */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t('revenueByChannel')}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {channelEntries.length === 0 && (
                  <p className="text-sm text-muted-foreground">{t('noData')}</p>
                )}
                {channelEntries.map(([channel, revenue]) => (
                  <div key={channel}>
                    <div className="flex justify-between text-sm mb-1">
                      <span>{tOrders(`channel.${channel}`)}</span>
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
                <CardTitle className="text-base">{t('ordersByStatus')}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {statusEntries.length === 0 && (
                  <p className="text-sm text-muted-foreground">{t('noData')}</p>
                )}
                {statusEntries.map(([status, count]) => (
                  <div key={status} className="flex justify-between text-sm">
                    <span>{tOrders(`status.${status}`)}</span>
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
                <CardTitle className="text-base">{t('topItems')}</CardTitle>
              </CardHeader>
              <CardContent>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-start pb-2 font-medium text-muted-foreground">{t('item')}</th>
                      <th className="text-end pb-2 font-medium text-muted-foreground">{t('qty')}</th>
                      <th className="text-end pb-2 font-medium text-muted-foreground">{t('revenueCol')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.topItems.map((item, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-2">{item.menuItemName}</td>
                        <td className="py-2 text-end tabular-nums">{item.qty}</td>
                        <td className="py-2 text-end tabular-nums font-medium">
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
  const { data, isLoading } = useSalesReport(locationId, { groupBy, startDate, endDate })

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
        <CsvExportButton locationId={locationId} params={{ reportType: 'sales', groupBy, startDate, endDate }} />
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
  const { data, isLoading } = useSalesByServerReport(locationId, {
    startDate,
    endDate,
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
            startDate,
            endDate,
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
  const t = useTranslations('reports')
  const tOrders = useTranslations('orders')
  const { data, isLoading } = useClosedOrdersReport(locationId, { startDate, endDate, status: status || undefined })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <label className="text-sm font-medium text-muted-foreground">{t('status')}</label>
          <Select
            value={status}
            onChange={(e) => setStatus(e.target.value as ClosedOrderStatusFilter | '')}
            className="w-40"
          >
            <option value="">{t('statusAll')}</option>
            <option value="paid">{tOrders('status.paid')}</option>
            <option value="cancelled">{tOrders('status.cancelled')}</option>
            <option value="other">{t('statusOther')}</option>
          </Select>
        </div>
        <CsvExportButton
          locationId={locationId}
          params={{ reportType: 'closed-orders', startDate, endDate, status: status || undefined }}
        />
      </div>
      {isLoading && <Spinner />}
      {data && <ClosedOrdersReportView report={data} />}
    </div>
  )
}

function DetailedReportsSection({ locationId }: { locationId: string }) {
  const t = useTranslations('reports')
  const [tab, setTab] = useState<ReportTab>('sales')
  const [startDate, setStartDate] = useState(isoDate(6))
  const [endDate, setEndDate] = useState(isoDate(0))

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-lg font-semibold">{t('detailedReports')}</h2>
        <DateRangeFields
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
        />
      </div>

      <div className="flex gap-1 rounded-lg border p-1 bg-muted w-fit">
        {TABS.map((tabValue) => (
          <button
            key={tabValue}
            onClick={() => setTab(tabValue)}
            className={`px-3 py-1 rounded-md text-sm transition-colors ${
              tab === tabValue ? 'bg-background shadow-sm font-medium' : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {t(TAB_KEY[tabValue])}
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
  const t = useTranslations('reports')
  const locationId = useAuthStore((s) => s.activeLocationId)

  return (
    <div className="p-6 space-y-10">
      <h1 className="text-2xl font-bold">{t('title')}</h1>
      <OverviewSection />
      {locationId && <DetailedReportsSection locationId={locationId} />}
    </div>
  )
}
