'use client'

import { use } from 'react'
import { useRouter } from 'next/navigation'
import { useOrder, useSubmitOrder, useCancelOrder } from '@/hooks/use-orders'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'
import type { OrderStatus, OrderItemStatus } from '@smartserve/types'

const ORDER_STATUS_VARIANT: Record<
  OrderStatus,
  'default' | 'secondary' | 'destructive' | 'outline'
> = {
  open: 'outline',
  submitted: 'secondary',
  preparing: 'secondary',
  ready: 'default',
  served: 'default',
  paid: 'default',
  cancelled: 'destructive',
}

const ITEM_STATUS_VARIANT: Record<
  OrderItemStatus,
  'default' | 'secondary' | 'destructive' | 'outline'
> = {
  pending: 'outline',
  preparing: 'secondary',
  ready: 'default',
  served: 'default',
  cancelled: 'destructive',
}

interface Props {
  params: Promise<{ orderId: string }>
}

export default function OrderDetailPage({ params }: Props) {
  const { orderId } = use(params)
  const router = useRouter()

  const { data: order, isLoading } = useOrder(orderId)
  const submitOrder = useSubmitOrder()
  const cancelOrder = useCancelOrder()

  async function handleSubmit() {
    if (!order) return
    await submitOrder.mutateAsync({ orderId, locationId: order.locationId })
  }

  async function handleCancel() {
    if (!order) return
    if (!confirm('Cancel this order?')) return
    await cancelOrder.mutateAsync({ orderId, locationId: order.locationId })
    router.push('/orders')
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <Spinner />
      </div>
    )
  }

  if (!order) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Order not found.</p>
        <Button variant="outline" className="mt-4" onClick={() => router.push('/orders')}>
          Back
        </Button>
      </div>
    )
  }

  const canSubmit = order.status === 'open' && order.items.length > 0
  const canCancel = !['paid', 'cancelled'].includes(order.status)

  return (
    <div className="p-6 space-y-6 max-w-2xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <Button variant="ghost" size="sm" onClick={() => router.push('/orders')} className="mb-1 -ml-2">
            ← Orders
          </Button>
          <h1 className="text-2xl font-bold">
            Order <span className="font-mono text-xl">#{order.id.slice(0, 8)}</span>
          </h1>
          <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
            {order.tableName && <span>{order.tableName}</span>}
            <span>·</span>
            <span className="capitalize">{order.channel.replace('_', ' ')}</span>
            <span>·</span>
            <span>{new Date(order.createdAt).toLocaleString('he-IL')}</span>
          </div>
        </div>
        <Badge
          variant={ORDER_STATUS_VARIANT[order.status as OrderStatus]}
          className="text-sm capitalize"
        >
          {order.status}
        </Badge>
      </div>

      {/* Items */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Items ({order.items.length})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {order.items.length === 0 && (
            <p className="text-sm text-muted-foreground">No items yet.</p>
          )}
          {order.items.map((item) => (
            <div
              key={item.id}
              className="flex items-start justify-between py-2 border-b last:border-0"
            >
              <div className="space-y-0.5">
                <p className="text-sm font-medium">
                  {item.qty}× {item.menuItemName}
                </p>
                {item.modifiers.length > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {item.modifiers.map((m) => m.name).join(', ')}
                  </p>
                )}
                {item.notes && (
                  <p className="text-xs text-muted-foreground italic">{item.notes}</p>
                )}
                <Badge
                  variant={ITEM_STATUS_VARIANT[item.status as OrderItemStatus]}
                  className="text-xs capitalize"
                >
                  {item.status}
                </Badge>
              </div>
              <span className="text-sm font-medium whitespace-nowrap">
                ₪{(item.unitPrice * item.qty).toFixed(2)}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Totals */}
      <Card>
        <CardContent className="p-4 space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Subtotal</span>
            <span>₪{order.subtotal.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Tax (17%)</span>
            <span>₪{order.taxAmount.toFixed(2)}</span>
          </div>
          <div className="flex justify-between font-bold text-base pt-1 border-t">
            <span>Total</span>
            <span>₪{order.total.toFixed(2)}</span>
          </div>
        </CardContent>
      </Card>

      {/* Notes */}
      {order.notes && (
        <p className="text-sm text-muted-foreground">
          <span className="font-medium">Notes: </span>
          {order.notes}
        </p>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        {canSubmit && (
          <Button onClick={handleSubmit} disabled={submitOrder.isPending}>
            Submit to Kitchen
          </Button>
        )}
        {canCancel && (
          <Button
            variant="outline"
            className="text-destructive hover:text-destructive"
            onClick={handleCancel}
            disabled={cancelOrder.isPending}
          >
            Cancel Order
          </Button>
        )}
      </div>
    </div>
  )
}
