'use client'

import { Badge } from '@/components/ui/badge'
import { useLocale, useTranslations } from 'next-intl'
import { formatPrice } from '@/lib/utils'
import type { ClosedOrdersReport } from '@smartserve/types'

const STATUS_VARIANT: Record<string, 'success' | 'destructive' | 'secondary'> = {
  paid: 'success',
  cancelled: 'destructive',
}

export function ClosedOrdersReportView({ report }: { report: ClosedOrdersReport }) {
  const t = useTranslations('reports')
  const tOrders = useTranslations('orders')
  const locale = useLocale()

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {t('ordersCount', { count: report.orders.length })}
      </p>

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="pb-2 text-start font-medium text-muted-foreground">{t('colOrder')}</th>
            <th className="pb-2 text-start font-medium text-muted-foreground">{t('colStatus')}</th>
            <th className="pb-2 text-start font-medium text-muted-foreground">{t('colChannel')}</th>
            <th className="pb-2 text-start font-medium text-muted-foreground">{t('colServer')}</th>
            <th className="pb-2 text-start font-medium text-muted-foreground">{t('colClosedAt')}</th>
            <th className="pb-2 text-end font-medium text-muted-foreground">{t('colTotal')}</th>
          </tr>
        </thead>
        <tbody>
          {report.orders.length === 0 && (
            <tr>
              <td colSpan={6} className="py-4 text-center text-muted-foreground">
                {t('noClosedOrders')}
              </td>
            </tr>
          )}
          {report.orders.map((order) => (
            <tr key={order.id} className="border-b last:border-0">
              <td className="py-2 font-mono text-xs">{order.id.slice(0, 8)}</td>
              <td className="py-2">
                <Badge variant={STATUS_VARIANT[order.status] ?? 'secondary'}>
                  {tOrders(`status.${order.status}`)}
                </Badge>
              </td>
              <td className="py-2">{tOrders(`channel.${order.channel}`)}</td>
              <td className="py-2">{order.createdByName ?? '—'}</td>
              <td className="py-2">{new Date(order.createdAt).toLocaleString(locale === 'he' ? 'he-IL' : 'en-US')}</td>
              <td className="py-2 text-end font-medium tabular-nums">{formatPrice(order.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
