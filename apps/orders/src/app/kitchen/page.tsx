'use client'

import { useMemo } from 'react'
import { useSearchParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'
import { useOrders, useOrder, useUpdateOrderItemStatus } from '@/hooks/use-orders'
import { useLocationWs } from '@/hooks/use-ws'
import { useAuthStore } from '@/lib/auth-store'
import { apiClient } from '@/lib/api'
import { Spinner } from '@/components/ui/spinner'
import type { OrderItemStatus, Printer, PrinterRoute } from '@smartserve/types'
import { itemMatchesStation, parseKitchenStation, type KitchenStation } from './station'
import { ticketAgeClass, ticketAgeMinutes } from './ticket-age'

const ITEM_NEXT_STATUS: Partial<Record<OrderItemStatus, OrderItemStatus>> = {
  pending: 'preparing',
  preparing: 'ready',
}

const ITEM_STATUS_STYLE: Record<OrderItemStatus, string> = {
  held: 'bg-zinc-900 border-zinc-700 text-zinc-500',
  pending: 'bg-zinc-800 border-zinc-600 text-zinc-100',
  preparing: 'bg-amber-900 border-amber-500 text-amber-100',
  ready: 'bg-green-900 border-green-500 text-green-100',
  served: 'bg-zinc-900 border-zinc-700 text-zinc-500',
  cancelled: 'bg-zinc-900 border-zinc-700 text-zinc-500 line-through',
}

function OrderCard({
  orderId,
  station,
  printers,
  routes,
}: {
  orderId: string
  station: KitchenStation
  printers: Printer[]
  routes: PrinterRoute[]
}) {
  const t = useTranslations('kitchen')
  const tItemStatus = useTranslations('itemStatus')
  const tOrders = useTranslations('orders')
  const { data: order } = useOrder(orderId)
  const updateStatus = useUpdateOrderItemStatus()

  if (!order) return null

  const stationItems = order.items.filter((i) => itemMatchesStation(i, station, printers, routes))
  const activeItems = stationItems.filter((i) => !['served', 'cancelled', 'held'].includes(i.status))
  const heldItems = stationItems.filter((i) => i.status === 'held')

  if (activeItems.length === 0 && heldItems.length === 0) return null

  async function bumpItem(itemId: string, current: OrderItemStatus) {
    const next = ITEM_NEXT_STATUS[current]
    if (!next) return
    await updateStatus.mutateAsync({ orderId, itemId, status: next })
  }

  async function bumpTicket() {
    for (const item of activeItems.filter((i) => i.status !== 'ready')) {
      await updateStatus.mutateAsync({ orderId, itemId: item.id, status: 'ready' })
    }
  }

  const allReady = activeItems.length > 0 && activeItems.every((i) => i.status === 'ready')
  const age = ticketAgeMinutes(activeItems)
  const tableLabel = order.tableName ?? tOrders(`channel.${order.channel}` as never)

  return (
    <div
      data-testid="kds-ticket"
      className="flex flex-col gap-3 rounded-xl border border-zinc-700 bg-zinc-900 p-4"
    >
      <div className="flex items-start justify-between gap-3 border-b border-zinc-700 pb-3">
        <div>
          <p className="text-2xl font-bold leading-tight">{tableLabel}</p>
          <p className="font-mono text-xl font-semibold text-zinc-200">
            #{order.orderNumber ?? order.id.slice(0, 6)}
          </p>
        </div>
        <div className="text-end">
          <p className={`text-lg font-semibold tabular-nums ${ticketAgeClass(age)}`}>
            {t('ageMinutes', { minutes: age })}
          </p>
          {allReady && (
            <span className="text-xs px-2 py-1 rounded bg-green-900 text-green-400 border border-green-700">
              {t('ready')}
            </span>
          )}
        </div>
      </div>

      {heldItems.length > 0 && (
        <div
          data-testid="course-waiting"
          className="rounded-lg border border-amber-700 bg-amber-950/60 px-3 py-2 text-amber-100"
        >
          {Array.from(new Set(heldItems.map((i) => i.fireCourse)))
            .sort((a, b) => a - b)
            .map((course) => (
              <p key={course} className="text-sm font-semibold">
                {t('courseWaiting', { n: course })}
              </p>
            ))}
        </div>
      )}

      <div className="space-y-2">
        {activeItems.map((item) => {
          const next = ITEM_NEXT_STATUS[item.status as OrderItemStatus]
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => bumpItem(item.id, item.status as OrderItemStatus)}
              disabled={!next}
              className={`min-h-16 w-full rounded-lg border p-3 text-start transition-colors ${
                ITEM_STATUS_STYLE[item.status as OrderItemStatus]
              } ${next ? 'hover:brightness-125 cursor-pointer' : 'cursor-default'}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-base font-semibold">
                  {item.qty}× {item.menuItemName}
                </span>
                <span className="text-xs uppercase tracking-wide opacity-70">
                  {tItemStatus(item.status)}
                </span>
              </div>
              {item.modifiers.length > 0 && (
                <p className="mt-0.5 text-sm font-bold">
                  {item.modifiers.map((m) => m.name).join(' · ')}
                </p>
              )}
              {item.notes && <p className="mt-0.5 text-sm font-bold italic">{item.notes}</p>}
            </button>
          )
        })}
      </div>

      {!allReady && activeItems.length > 0 && (
        <button
          type="button"
          data-testid="bump-ticket"
          onClick={() => void bumpTicket()}
          className="min-h-16 rounded-lg bg-green-700 px-4 text-base font-semibold text-white hover:bg-green-600"
        >
          {t('bumpTicket')}
        </button>
      )}
    </div>
  )
}

function KitchenBoard() {
  const t = useTranslations('kitchen')
  const searchParams = useSearchParams()
  const station = parseKitchenStation(searchParams.get('station'))
  const locationId = useAuthStore((s) => s.activeLocationId)
  const { data: submitted, isLoading: l1 } = useOrders(locationId, 'submitted')
  const { data: preparing, isLoading: l2 } = useOrders(locationId, 'preparing')
  const { data: ready, isLoading: l3 } = useOrders(locationId, 'ready')
  const { data: printers = [] } = useQuery({
    queryKey: ['printers', locationId],
    queryFn: () => apiClient.printers.list(locationId!),
    enabled: !!locationId,
  })
  const { data: routes = [] } = useQuery({
    queryKey: ['printer-routes', locationId],
    queryFn: () => apiClient.printers.listRoutes(locationId!),
    enabled: !!locationId,
  })

  useLocationWs(locationId)

  const activeOrders = useMemo(
    () =>
      [...(submitted ?? []), ...(preparing ?? []), ...(ready ?? [])].sort(
        (a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(),
      ),
    [submitted, preparing, ready],
  )

  const isLoading = l1 || l2 || l3

  return (
    <main className="min-h-screen space-y-4 p-4">
      <div className="flex items-center justify-between gap-3 border-b border-zinc-800 py-2">
        <h1 className="text-xl font-bold tracking-wide text-zinc-100">🍳 {t('title')}</h1>
        <div className="flex items-center gap-3">
          <a
            href="/kitchen?station=kitchen"
            className={`flex min-h-12 items-center rounded-md px-4 text-sm font-medium ${
              station === 'kitchen' ? 'bg-zinc-100 text-zinc-950' : 'text-zinc-300 hover:text-zinc-100'
            }`}
          >
            {t('stationKitchen')}
          </a>
          <a
            href="/kitchen?station=bar"
            className={`flex min-h-12 items-center rounded-md px-4 text-sm font-medium ${
              station === 'bar' ? 'bg-zinc-100 text-zinc-950' : 'text-zinc-300 hover:text-zinc-100'
            }`}
          >
            {t('stationBar')}
          </a>
          <span className="text-sm text-zinc-300">{t('activeOrders', { count: activeOrders.length })}</span>
        </div>
      </div>

      {isLoading && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}

      {!isLoading && activeOrders.length === 0 && (
        <div className="flex flex-col items-center justify-center space-y-2 py-24 text-zinc-600">
          <p className="text-5xl">✓</p>
          <p className="text-lg">{t('allCaughtUp')}</p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {activeOrders.map((o) => (
          <OrderCard
            key={o.id}
            orderId={o.id}
            station={station}
            printers={printers}
            routes={routes}
          />
        ))}
      </div>
    </main>
  )
}

export default function KitchenPage() {
  return <KitchenBoard />
}
