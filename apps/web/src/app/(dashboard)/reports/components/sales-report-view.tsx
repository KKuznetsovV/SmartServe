'use client'

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useTranslations } from 'next-intl'
import { formatPrice } from '@/lib/utils'
import type { SalesReport } from '@smartserve/types'

export function SalesReportView({ report }: { report: SalesReport }) {
  const t = useTranslations('reports')
  const chartData = report.rows
    .slice()
    .sort((a, b) => b.revenue - a.revenue)
    .slice(0, 10)
    .map((row) => ({ label: row.groupLabel, revenue: row.revenue }))

  return (
    <div className="space-y-4">
      <div className="flex gap-6 text-sm">
        <p>
          {t('totalQty')}: <span className="font-medium tabular-nums">{report.totalQty}</span>
        </p>
        <p>
          {t('totalRevenue')}: <span className="font-medium tabular-nums">{formatPrice(report.totalRevenue)}</span>
        </p>
      </div>

      {chartData.length > 0 && (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
                interval={0}
                angle={-20}
                textAnchor="end"
                height={50}
              />
              <YAxis tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} />
              <Tooltip
                formatter={(value: number) => formatPrice(value)}
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  color: 'hsl(var(--card-foreground))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: 'var(--radius)',
                }}
                labelStyle={{ color: 'hsl(var(--card-foreground))' }}
              />
              <Bar dataKey="revenue" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="pb-2 text-start font-medium text-muted-foreground">
              {report.groupBy === 'item' ? t('groupBy_item') : report.groupBy === 'category' ? t('groupBy_category') : t('groupBy_menu')}
            </th>
            <th className="pb-2 text-end font-medium text-muted-foreground">{t('qty')}</th>
            <th className="pb-2 text-end font-medium text-muted-foreground">{t('revenueCol')}</th>
          </tr>
        </thead>
        <tbody>
          {report.rows.length === 0 && (
            <tr>
              <td colSpan={3} className="py-4 text-center text-muted-foreground">
                {t('noSalesInRange')}
              </td>
            </tr>
          )}
          {report.rows.map((row, i) => (
            <tr key={row.groupId ?? i} className="border-b last:border-0">
              <td className="py-2">{row.groupLabel}</td>
              <td className="py-2 text-end tabular-nums">{row.qty}</td>
              <td className="py-2 text-end font-medium tabular-nums">{formatPrice(row.revenue)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
