'use client'

import { use, useState } from 'react'
import { useRouter } from 'next/navigation'
import { DndContext, useDroppable, useSensor, useSensors, PointerSensor, type DragEndEvent } from '@dnd-kit/core'
import { useOrder, useSubmitOrder, useCancelOrder, useAddOrderItem } from '@/hooks/use-orders'
import { useOrderPayments } from '@/hooks/use-payments'
import { useApplyDiscount } from '@/hooks/use-discounts'
import { PaymentDialog } from './payment-dialog'
import { MenuPanel } from './menu-panel'
import { ItemConfigDialog, type ItemConfigResult } from './item-config-dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'
import type { OrderStatus, OrderItemStatus, PaymentMethod, MenuItem } from '@smartserve/types'

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

const PAYMENT_METHOD_LABEL: Record<PaymentMethod, string> = {
  cash: 'Cash',
  card: 'Credit Card',
  tap: 'Tap to Pay',
  mobile: 'Mobile Pay',
  voucher: 'Voucher',
}

interface Props {
  params: Promise<{ orderId: string }>
}

export default function OrderDetailPage({ params }: Props) {
  const { orderId } = use(params)
  const router = useRouter()
  const [paymentOpen, setPaymentOpen] = useState(false)
  const [configuringItem, setConfiguringItem] = useState<MenuItem | null>(null)
  const [discountCode, setDiscountCode] = useState('')

  const { data: order, isLoading } = useOrder(orderId)
  const { data: payments } = useOrderPayments(orderId)
  const submitOrder = useSubmitOrder()
  const cancelOrder = useCancelOrder()
  const applyDiscount = useApplyDiscount()
  const addItem = useAddOrderItem()
  const { setNodeRef: setDropRef, isOver } = useDroppable({ id: 'order-drop-zone' })
  // A distance threshold keeps a plain tap from being swallowed as a zero-distance drag
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }))

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

  // Items without modifier groups add instantly (tap or drop); items with modifiers
  // always need explicit configuration first, whether tapped or dropped onto the order.
  function handleItemChosen(item: MenuItem) {
    if (!order) return
    if (item.modifierGroups.length > 0) {
      setConfiguringItem(item)
      return
    }
    addItem.mutate({
      orderId,
      locationId: order.locationId,
      item: { menuItemId: item.id, menuItemName: item.name, qty: 1, unitPrice: item.price, modifiers: [] },
    })
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (over?.id !== 'order-drop-zone') return
    const item = active.data.current?.item as MenuItem | undefined
    if (item) handleItemChosen(item)
  }

  function handleConfigConfirm(result: ItemConfigResult) {
    if (!configuringItem || !order) return
    addItem.mutate(
      {
        orderId,
        locationId: order.locationId,
        item: {
          menuItemId: configuringItem.id,
          menuItemName: configuringItem.name,
          qty: result.qty,
          unitPrice: result.unitPrice,
          modifiers: result.modifiers,
          notes: result.notes,
        },
      },
      { onSuccess: () => setConfiguringItem(null) },
    )
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
  const canPay = !['paid', 'cancelled', 'open'].includes(order.status)
  const canAddItems = ['open', 'submitted'].includes(order.status)

  const paidAmount = (payments ?? []).reduce((sum: number, p) => sum + p.amount, 0)
  const remaining = Math.max(0, order.total - paidAmount)

  return (
    <div className="p-4 md:p-6 space-y-6">
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

      <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
        <div className={canAddItems ? 'grid gap-6 md:grid-cols-[1fr_380px] items-start' : 'max-w-2xl mx-auto space-y-6'}>
          {canAddItems && <MenuPanel locationId={order.locationId} onItemTap={handleItemChosen} />}

          <div className="space-y-6 md:sticky md:top-6">
      {/* Items */}
      <Card ref={setDropRef} className={cn(canAddItems && isOver && 'ring-2 ring-primary')}>
        <CardHeader className="pb-2 flex-row items-center justify-between">
          <CardTitle className="text-base">Items ({order.items.length})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {order.items.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No items yet.
              {canAddItems && ' Tap or drag an item from the menu to add it.'}
            </p>
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
          {order.discountAmount > 0 && (
            <div className="flex justify-between text-sm text-emerald-600">
              <span>Discount</span>
              <span>−₪{order.discountAmount.toFixed(2)}</span>
            </div>
          )}
          <div className="flex justify-between font-bold text-base pt-1 border-t">
            <span>Total</span>
            <span>₪{order.total.toFixed(2)}</span>
          </div>
          {paidAmount > 0 && (
            <>
              <div className="flex justify-between text-sm text-green-600">
                <span>Paid</span>
                <span>−₪{paidAmount.toFixed(2)}</span>
              </div>
              <div className="flex justify-between font-semibold text-sm pt-1 border-t">
                <span>Remaining</span>
                <span>₪{remaining.toFixed(2)}</span>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Apply discount */}
      {['open', 'submitted'].includes(order.status) && !order.discountId && (
        <div className="flex gap-2">
          <Input
            placeholder="Discount code"
            value={discountCode}
            onChange={(e) => setDiscountCode(e.target.value)}
            className="max-w-xs uppercase"
          />
          <Button
            variant="outline"
            disabled={!discountCode.trim() || applyDiscount.isPending}
            onClick={() => {
              applyDiscount.mutate({ orderId, code: discountCode.trim() })
              setDiscountCode('')
            }}
          >
            Apply
          </Button>
        </div>
      )}

      {/* Payments list */}
      {payments && payments.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Payments</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {payments.map((p) => (
              <div key={p.id} className="flex justify-between items-center text-sm py-1 border-b last:border-0">
                <div>
                  <span className="font-medium">
                    {PAYMENT_METHOD_LABEL[p.method as PaymentMethod]}
                  </span>
                  <span className="ml-2 text-xs text-muted-foreground">
                    {new Date(p.createdAt).toLocaleTimeString('he-IL')}
                  </span>
                </div>
                <span className="font-medium">₪{p.amount.toFixed(2)}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

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
        {canPay && remaining > 0 && (
          <Button onClick={() => setPaymentOpen(true)}>Collect Payment</Button>
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
        </div>
      </DndContext>

      <PaymentDialog
        open={paymentOpen}
        onOpenChange={setPaymentOpen}
        orderId={orderId}
        remaining={remaining}
      />
      <ItemConfigDialog
        item={configuringItem}
        onOpenChange={(open) => !open && setConfiguringItem(null)}
        onConfirm={handleConfigConfirm}
        pending={addItem.isPending}
      />
    </div>
  )
}
