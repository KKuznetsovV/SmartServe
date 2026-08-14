'use client'

import { Badge } from '@/components/ui/badge'
import { formatPrice } from '@/lib/utils'
import type { ClosedOrdersReport } from '@smartserve/types'

const STATUS_VARIANT: Record<string, 'success' | 'destructive' | 'secondary'> = {
  paid: 'success',
  cancelled: 'destructive',
}

export function ClosedOrdersReportView({ report }: { report: ClosedOrdersReport }) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {report.orders.length} order{report.orders.length === 1 ? '' : 's'}
      </p>

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="pb-2 text-left font-medium text-muted-foreground">Order</th>
            <th className="pb-2 text-left font-medium text-muted-foreground">Status</th>
            <th className="pb-2 text-left font-medium text-muted-foreground">Channel</th>
            <th className="pb-2 text-left font-medium text-muted-foreground">Server</th>
            <th className="pb-2 text-left font-medium text-muted-foreground">Closed at</th>
            <th className="pb-2 text-right font-medium text-muted-foreground">Total</th>
          </tr>
        </thead>
        <tbody>
          {report.orders.length === 0 && (
            <tr>
              <td colSpan={6} className="py-4 text-center text-muted-foreground">
                No closed orders in this range
              </td>
            </tr>
          )}
          {report.orders.map((order) => (
            <tr key={order.id} className="border-b last:border-0">
              <td className="py-2 font-mono text-xs">{order.id.slice(0, 8)}</td>
              <td className="py-2">
                <Badge variant={STATUS_VARIANT[order.status] ?? 'secondary'} className="capitalize">
                  {order.status}
                </Badge>
              </td>
              <td className="py-2 capitalize">{order.channel.replace('_', ' ')}</td>
              <td className="py-2">{order.createdByName ?? '—'}</td>
              <td className="py-2">{new Date(order.createdAt).toLocaleString()}</td>
              <td className="py-2 text-right font-medium tabular-nums">{formatPrice(order.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
