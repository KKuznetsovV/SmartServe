'use client'

import { use, useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { apiClient } from '@/lib/api'
import type { Order } from '@smartserve/types'

const STATUS_STYLE: Record<string, { bg: string; text: string }> = {
  submitted: { bg: 'bg-zinc-800', text: 'text-zinc-100' },
  preparing: { bg: 'bg-amber-500', text: 'text-amber-950' },
  ready: { bg: 'bg-emerald-500', text: 'text-emerald-950' },
}

interface Props {
  params: Promise<{ locationId: string }>
}

export default function CustomerDisplayPage({ params }: Props) {
  const { locationId } = use(params)
  const t = useTranslations('display')
  const tOrders = useTranslations('orders')
  const [orders, setOrders] = useState<Order[]>([])
  const [lastUpdated, setLastUpdated] = useState(new Date())

  async function refresh() {
    try {
      const data = await apiClient.orders.publicActive(locationId)
      setOrders(data)
      setLastUpdated(new Date())
    } catch {
      // silently retry on next interval
    }
  }

  useEffect(() => {
    refresh()
    const interval = setInterval(refresh, 8_000)
    return () => clearInterval(interval)
  }, [locationId])

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold tracking-tight">{t('title')}</h1>
        <p className="text-sm text-zinc-500">
          {t('updated', { time: lastUpdated.toLocaleTimeString('he-IL') })}
        </p>
      </div>

      {orders.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-zinc-500">
          <p className="text-xl">{t('noActiveOrders')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {orders.map((order) => {
            const style = STATUS_STYLE[order.status] ?? STATUS_STYLE.submitted
            const statusLabel =
              order.status === 'preparing'
                ? t('preparing')
                : order.status === 'ready'
                  ? t('ready')
                  : t('received')
            return (
              <div
                key={order.id}
                className={`rounded-2xl p-5 ${style.bg} ${style.text} flex flex-col gap-3`}
              >
                {/* Order number + status */}
                <div className="flex items-center justify-between">
                  <span className="text-2xl font-bold font-mono">
                    #{order.id.slice(0, 6).toUpperCase()}
                  </span>
                  <span className="text-sm font-semibold uppercase tracking-wide opacity-80">
                    {statusLabel}
                  </span>
                </div>

                {/* Table / channel */}
                <p className="text-sm opacity-70 capitalize">
                  {order.tableName ?? tOrders(`channel.${order.channel}` as never)}
                </p>

                {/* Items */}
                <ul className="text-sm space-y-0.5">
                  {order.items.map((item) => (
                    <li key={item.id}>
                      {item.qty}× {item.menuItemName}
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
