'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'
import { apiClient } from '@/lib/api'
import { useDeviceStore } from '@/lib/device-store'
import { useAuthReady } from '@/hooks/use-auth-ready'
import { useLocationWs } from '@/hooks/use-ws'

const STATUS_STYLE: Record<string, { bg: string; text: string }> = {
  submitted: { bg: 'bg-zinc-800', text: 'text-zinc-100' },
  preparing: { bg: 'bg-amber-500', text: 'text-amber-950' },
  ready: { bg: 'bg-emerald-500', text: 'text-emerald-950' },
}

export default function CustomerDisplayPage() {
  const router = useRouter()
  const t = useTranslations('display')
  const { ready, deviceConfigured } = useAuthReady()
  const locationId = useDeviceStore((s) => s.locationId)
  const deviceToken = useDeviceStore((s) => s.deviceToken)
  const deviceType = useDeviceStore((s) => s.deviceType)

  useEffect(() => {
    if (ready && (!deviceConfigured || deviceType !== 'display')) {
      router.replace('/setup')
    }
  }, [ready, deviceConfigured, deviceType, router])

  const { data: orders = [], dataUpdatedAt } = useQuery({
    queryKey: ['orders', locationId, 'display'],
    queryFn: () => apiClient.orders.publicDisplay(deviceToken as string),
    enabled: Boolean(deviceToken && deviceType === 'display'),
    refetchInterval: 15_000,
  })

  useLocationWs(deviceType === 'display' ? locationId : null)

  const lastUpdated = dataUpdatedAt ? new Date(dataUpdatedAt) : new Date()

  if (!ready || !deviceConfigured || deviceType !== 'display') {
    return null
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white p-6">
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
                key={`${order.orderNumber}-${order.updatedAt}`}
                className={`rounded-2xl p-5 ${style.bg} ${style.text} flex flex-col gap-3`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-2xl font-bold font-mono">#{order.orderNumber}</span>
                  <span className="text-sm font-semibold uppercase tracking-wide opacity-80">
                    {statusLabel}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
