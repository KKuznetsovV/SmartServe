'use client'

import { useOrders, useOrder, useUpdateOrderItemStatus } from '@/hooks/use-orders'
import { useLocationWs } from '@/hooks/use-ws'
import { useAuthStore } from '@/lib/auth-store'
import { Spinner } from '@/components/ui/spinner'
import type { OrderItemStatus } from '@smartserve/types'

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

const ACTIVE_STATUSES = ['submitted', 'preparing']

function OrderCard({ orderId }: { orderId: string }) {
  const { data: order } = useOrder(orderId)
  const updateStatus = useUpdateOrderItemStatus()

  if (!order) return null

  const activeItems = order.items.filter(
    (i) => !['served', 'cancelled', 'held'].includes(i.status),
  )

  if (activeItems.length === 0) return null

  async function bumpItem(itemId: string, current: OrderItemStatus) {
    const next = ITEM_NEXT_STATUS[current]
    if (!next) return
    await updateStatus.mutateAsync({ orderId, itemId, status: next })
  }

  async function markAllReady() {
    for (const item of activeItems.filter((i) => i.status !== 'ready')) {
      await updateStatus.mutateAsync({ orderId, itemId: item.id, status: 'ready' })
    }
  }

  const allReady = activeItems.every((i) => i.status === 'ready')

  return (
    <div className="bg-zinc-900 border border-zinc-700 rounded-xl p-4 flex flex-col gap-3">
      {/* Order header */}
      <div className="flex items-center justify-between border-b border-zinc-700 pb-2">
        <div>
          <span className="font-mono text-lg font-bold">#{order.id.slice(0, 6)}</span>
          {order.tableName && (
            <span className="ml-2 text-zinc-400 text-sm">{order.tableName}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500 capitalize">
            {order.channel.replace('_', ' ')}
          </span>
          {!allReady && (
            <button
              onClick={markAllReady}
              className="text-xs px-2 py-1 rounded bg-green-700 hover:bg-green-600 text-white transition-colors"
            >
              All Ready ✓
            </button>
          )}
          {allReady && (
            <span className="text-xs px-2 py-1 rounded bg-green-900 text-green-400 border border-green-700">
              ✓ Ready
            </span>
          )}
        </div>
      </div>

      {/* Items */}
      <div className="space-y-2">
        {activeItems.map((item) => {
          const next = ITEM_NEXT_STATUS[item.status as OrderItemStatus]
          return (
            <button
              key={item.id}
              onClick={() => bumpItem(item.id, item.status as OrderItemStatus)}
              disabled={!next}
              className={`w-full text-left rounded-lg border p-3 transition-colors ${
                ITEM_STATUS_STYLE[item.status as OrderItemStatus]
              } ${next ? 'hover:brightness-125 cursor-pointer' : 'cursor-default'}`}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-base">
                  {item.qty}× {item.menuItemName}
                </span>
                <span className="text-xs uppercase tracking-wide opacity-70">
                  {item.status}
                </span>
              </div>
              {item.modifiers.length > 0 && (
                <p className="text-xs opacity-60 mt-0.5">
                  {item.modifiers.map((m) => m.name).join(' · ')}
                </p>
              )}
              {item.notes && (
                <p className="text-xs italic opacity-60 mt-0.5">{item.notes}</p>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function KitchenPage() {
  const locationId = useAuthStore((s) => s.activeLocationId)
  const { data: submitted, isLoading: l1 } = useOrders(locationId, 'submitted')
  const { data: preparing, isLoading: l2 } = useOrders(locationId, 'preparing')

  useLocationWs(locationId)

  const activeOrders = [
    ...(submitted ?? []),
    ...(preparing ?? []),
  ].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime())

  const isLoading = l1 || l2

  return (
    <div className="min-h-screen p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between py-2 border-b border-zinc-800">
        <h1 className="text-xl font-bold tracking-wide text-zinc-100">
          🍳 Kitchen Display
        </h1>
        <div className="flex items-center gap-3 text-sm text-zinc-400">
          <span>{activeOrders.length} active order{activeOrders.length !== 1 ? 's' : ''}</span>
          <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
        </div>
      </div>

      {isLoading && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}

      {!isLoading && activeOrders.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-zinc-600 space-y-2">
          <p className="text-5xl">✓</p>
          <p className="text-lg">All caught up</p>
        </div>
      )}

      {/* Order grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {activeOrders.map((o) => (
          <OrderCard key={o.id} orderId={o.id} />
        ))}
      </div>
    </div>
  )
}
