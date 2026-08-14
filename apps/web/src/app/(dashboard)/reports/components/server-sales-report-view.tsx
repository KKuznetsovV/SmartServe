'use client'

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatPrice } from '@/lib/utils'
import type { ServerSalesReport } from '@smartserve/types'

export function ServerSalesReportView({ report }: { report: ServerSalesReport }) {
  const filtered = Boolean(report.itemId || report.categoryId)
  const chartData = report.rows
    .slice()
    .sort((a, b) => b.revenue - a.revenue)
    .slice(0, 10)
    .map((row) => ({ label: row.serverName, revenue: row.revenue }))

  return (
    <div className="space-y-4">
      {chartData.length > 0 && (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 12 }} interval={0} angle={-20} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value: number) => formatPrice(value)} />
              <Bar dataKey="revenue" fill="var(--primary)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="pb-2 text-left font-medium text-muted-foreground">Server</th>
            <th className="pb-2 text-right font-medium text-muted-foreground">Orders</th>
            {filtered && <th className="pb-2 text-right font-medium text-muted-foreground">Qty</th>}
            <th className="pb-2 text-right font-medium text-muted-foreground">Revenue</th>
          </tr>
        </thead>
        <tbody>
          {report.rows.length === 0 && (
            <tr>
              <td colSpan={filtered ? 4 : 3} className="py-4 text-center text-muted-foreground">
                No sales in this range
              </td>
            </tr>
          )}
          {report.rows.map((row, i) => (
            <tr key={row.serverId ?? i} className="border-b last:border-0">
              <td className="py-2">{row.serverName}</td>
              <td className="py-2 text-right tabular-nums">{row.orderCount}</td>
              {filtered && <td className="py-2 text-right tabular-nums">{row.qty ?? 0}</td>}
              <td className="py-2 text-right font-medium tabular-nums">{formatPrice(row.revenue)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
