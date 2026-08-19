'use client'

import { use, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  DndContext,
  DragOverlay,
  useDroppable,
  useSensor,
  useSensors,
  PointerSensor,
  type DragStartEvent,
  type DragEndEvent,
} from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy, arrayMove } from '@dnd-kit/sortable'
import {
  useOrder,
  useSubmitOrder,
  useCancelOrder,
  useAddOrderItem,
  useUpdateOrderItemStatus,
  useUpdateOrderItem,
  useReorderOrderItems,
  useRemoveOrderItem,
  useFireCourse,
  useSetItemComp,
  useDeleteOrderItems,
} from '@/hooks/use-orders'
import { useMenuItem } from '@/hooks/use-menu'
import { useOrderPayments } from '@/hooks/use-payments'
import { useApplyDiscount } from '@/hooks/use-discounts'
import { PaymentDialog } from './payment-dialog'
import { MenuPanel, MenuItemCardPreview } from './menu-panel'
import { ItemConfigDialog, type ItemConfigResult } from './item-config-dialog'
import { OrderItemRow, OrderItemRowPreview } from './order-item-row'
import { CancelDropZone } from './cancel-drop-zone'
import { GuestAssignDialog } from './guest-assign-dialog'
import { ItemDiscountDialog } from './item-discount-dialog'
import { ManagerOverrideDialog } from './manager-override-dialog'
import { QuantitySelectDialog } from './quantity-select-dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { cn } from '@/lib/utils'
import type { ItemSelection } from '@smartserve/api-client'
import type { OrderStatus, PaymentMethod, MenuItem, OrderItem } from '@smartserve/types'

type ActiveDrag = { type: 'menu-item'; item: MenuItem } | { type: 'order-item'; item: OrderItem }
type BulkAction = 'guest' | 'discount' | 'comp-on' | 'comp-off' | 'delete'

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
  split: 'secondary',
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
  const [editingItem, setEditingItem] = useState<OrderItem | null>(null)
  const [discountCode, setDiscountCode] = useState('')
  const [activeDrag, setActiveDrag] = useState<ActiveDrag | null>(null)
  const [selectMode, setSelectMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [guestDialogOpen, setGuestDialogOpen] = useState(false)
  const [discountDialogOpen, setDiscountDialogOpen] = useState(false)
  const [overrideOpen, setOverrideOpen] = useState(false)
  const [qtyDialogOpen, setQtyDialogOpen] = useState(false)
  const [pendingAction, setPendingAction] = useState<BulkAction | null>(null)
  const [activeSelections, setActiveSelections] = useState<ItemSelection[]>([])

  const { data: order, isLoading } = useOrder(orderId)
  const { data: payments } = useOrderPayments(orderId)
  const { data: editingMenuItem } = useMenuItem(editingItem?.menuItemId ?? null)
  const submitOrder = useSubmitOrder()
  const cancelOrder = useCancelOrder()
  const applyDiscount = useApplyDiscount()
  const addItem = useAddOrderItem()
  const updateItemStatus = useUpdateOrderItemStatus()
  const updateItem = useUpdateOrderItem()
  const reorderItems = useReorderOrderItems()
  const removeItem = useRemoveOrderItem()
  const fireCourse = useFireCourse()
  const setItemComp = useSetItemComp()
  const deleteItems = useDeleteOrderItems()
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

  function handleDragStart(event: DragStartEvent) {
    const data = event.active.data.current as ActiveDrag | undefined
    if (data) setActiveDrag(data)
  }

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    setActiveDrag(null)
    const data = active.data.current as ActiveDrag | undefined
    if (!data || !order) return

    if (data.type === 'menu-item') {
      // Dropping anywhere over the items card counts as adding to the order — the
      // card itself and each existing row are separate droppable regions.
      const orderItemIds = new Set(order.items.map((i) => i.id))
      if (over && (over.id === 'order-drop-zone' || orderItemIds.has(String(over.id)))) {
        handleItemChosen(data.item)
      }
      return
    }

    // Dragging an existing order item: drop on the trash zone to remove it
    // (or cancel it, once the order has already been submitted), or drop on
    // another item to reorder the list.
    if (over?.id === 'cancel-zone') {
      if (order.status === 'open') {
        removeItem.mutate({ orderId, itemId: data.item.id })
      } else {
        updateItemStatus.mutate({ orderId, itemId: data.item.id, status: 'cancelled' })
      }
      return
    }
    if (over && over.id !== active.id) {
      const ids = order.items.map((i) => i.id)
      const oldIndex = ids.indexOf(String(active.id))
      const newIndex = ids.indexOf(String(over.id))
      if (oldIndex !== -1 && newIndex !== -1) {
        reorderItems.mutate({ orderId, ids: arrayMove(ids, oldIndex, newIndex) })
      }
    }
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
          fireCourse: result.fireCourse,
        },
      },
      { onSuccess: () => setConfiguringItem(null) },
    )
  }

  function handleEditConfirm(result: ItemConfigResult) {
    if (!editingItem) return
    updateItem.mutate(
      {
        orderId,
        itemId: editingItem.id,
        data: { qty: result.qty, notes: result.notes, modifiers: result.modifiers, fireCourse: result.fireCourse },
      },
      { onSuccess: () => setEditingItem(null) },
    )
  }

  function toggleSelected(itemId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(itemId)) next.delete(itemId)
      else next.add(itemId)
      return next
    })
  }

  function exitSelectMode() {
    setSelectMode(false)
    setSelectedIds(new Set())
  }

  /** Entry point for every group-action button — if any selected item has more than
   * one unit, ask how many units to apply the action to before running it. */
  function startBulkAction(action: BulkAction) {
    if (!order) return
    const multiQtyItems = order.items.filter((i) => selectedIds.has(i.id) && i.qty > 1)
    if (multiQtyItems.length > 0) {
      setPendingAction(action)
      setQtyDialogOpen(true)
    } else {
      runBulkAction(action, Array.from(selectedIds).map((itemId) => ({ itemId })))
    }
  }

  function handleQuantityConfirm(quantities: Record<string, number>) {
    setQtyDialogOpen(false)
    const selections = Array.from(selectedIds).map((itemId) => ({ itemId, quantity: quantities[itemId] }))
    if (pendingAction) runBulkAction(pendingAction, selections)
    setPendingAction(null)
  }

  function runBulkAction(action: BulkAction, selections: ItemSelection[]) {
    switch (action) {
      case 'guest':
        setActiveSelections(selections)
        setGuestDialogOpen(true)
        break
      case 'discount':
        setActiveSelections(selections)
        setDiscountDialogOpen(true)
        break
      case 'comp-on':
        handleMarkComp(true, selections)
        break
      case 'comp-off':
        handleMarkComp(false, selections)
        break
      case 'delete':
        handleDeleteSelected(selections)
        break
    }
  }

  async function handleMarkComp(comped: boolean, selections: ItemSelection[]) {
    if (selections.length === 0) return
    await setItemComp.mutateAsync({ orderId, items: selections, comped })
    exitSelectMode()
  }

  async function handleDeleteSelected(selections: ItemSelection[]) {
    if (selections.length === 0 || !order) return
    if (order.status === 'open') {
      if (!confirm(`Delete ${selections.length} item(s)?`)) return
      await deleteItems.mutateAsync({ orderId, items: selections })
      exitSelectMode()
    } else {
      setActiveSelections(selections)
      setOverrideOpen(true)
    }
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
  const canSelectItems = !['paid', 'cancelled'].includes(order.status) && order.items.length > 0

  const heldCourses = Array.from(
    new Set(order.items.filter((i) => i.status === 'held').map((i) => i.fireCourse)),
  ).sort((a, b) => a - b)

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

      <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
        <div className={canAddItems ? 'grid gap-6 md:grid-cols-[1fr_380px] items-start' : 'max-w-2xl mx-auto space-y-6'}>
          {canAddItems && <MenuPanel locationId={order.locationId} onItemTap={handleItemChosen} />}

          <div className="space-y-6 md:sticky md:top-6">
      {/* Items */}
      <Card ref={setDropRef} className={cn(canAddItems && isOver && 'ring-2 ring-primary')}>
        <CardHeader className="pb-2 flex-row items-center justify-between">
          <CardTitle className="text-base">Items ({order.items.length})</CardTitle>
          {canSelectItems && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => (selectMode ? exitSelectMode() : setSelectMode(true))}
            >
              {selectMode ? 'Done' : 'Select'}
            </Button>
          )}
        </CardHeader>
        <CardContent className="space-y-2">
          {order.items.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No items yet.
              {canAddItems && ' Tap or drag an item from the menu to add it.'}
            </p>
          )}
          <SortableContext items={order.items.map((i) => i.id)} strategy={verticalListSortingStrategy}>
            {order.items.map((item) => (
              <OrderItemRow
                key={item.id}
                item={item}
                draggable={canAddItems}
                onEdit={setEditingItem}
                selectable={selectMode}
                selected={selectedIds.has(item.id)}
                onToggleSelect={toggleSelected}
              />
            ))}
          </SortableContext>
        </CardContent>
      </Card>

      {selectMode && selectedIds.size > 0 && (
        <Card className="border-primary">
          <CardContent className="p-3 flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium mr-1">{selectedIds.size} selected</span>
            <Button variant="outline" size="sm" onClick={() => startBulkAction('guest')}>
              Assign to Guest
            </Button>
            <Button variant="outline" size="sm" onClick={() => startBulkAction('discount')}>
              Discount
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => startBulkAction('comp-on')}
              disabled={setItemComp.isPending}
            >
              On the House
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => startBulkAction('comp-off')}
              disabled={setItemComp.isPending}
            >
              Remove Comp
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => startBulkAction('delete')}
              disabled={deleteItems.isPending}
            >
              Delete
            </Button>
          </CardContent>
        </Card>
      )}

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
        {['submitted', 'preparing', 'ready'].includes(order.status) &&
          heldCourses.map((course) => (
            <Button
              key={course}
              variant="outline"
              disabled={fireCourse.isPending}
              onClick={() => fireCourse.mutate({ orderId, course })}
            >
              Fire Course {course}
            </Button>
          ))}
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

        <DragOverlay>
          {activeDrag?.type === 'menu-item' && <MenuItemCardPreview item={activeDrag.item} />}
          {activeDrag?.type === 'order-item' && <OrderItemRowPreview item={activeDrag.item} />}
        </DragOverlay>
        <CancelDropZone
          visible={activeDrag?.type === 'order-item'}
          mode={order.status === 'open' ? 'remove' : 'cancel'}
        />
      </DndContext>

      <PaymentDialog
        open={paymentOpen}
        onOpenChange={setPaymentOpen}
        orderId={orderId}
        order={order}
        payments={payments ?? []}
        remaining={remaining}
      />
      <GuestAssignDialog
        open={guestDialogOpen}
        onOpenChange={setGuestDialogOpen}
        orderId={orderId}
        items={activeSelections}
        guestCount={order.guestCount ?? 2}
        onDone={exitSelectMode}
      />
      <ItemDiscountDialog
        open={discountDialogOpen}
        onOpenChange={setDiscountDialogOpen}
        orderId={orderId}
        items={activeSelections}
        onDone={exitSelectMode}
      />
      <QuantitySelectDialog
        open={qtyDialogOpen}
        onOpenChange={setQtyDialogOpen}
        items={order.items.filter((i) => selectedIds.has(i.id) && i.qty > 1)}
        onConfirm={handleQuantityConfirm}
      />
      <ManagerOverrideDialog
        open={overrideOpen}
        onOpenChange={setOverrideOpen}
        locationId={order.locationId}
        title="Delete Submitted Item(s)"
        description="These items have already been sent to the kitchen. A manager must approve deleting them."
        pending={deleteItems.isPending}
        onConfirm={async (override) => {
          await deleteItems.mutateAsync({ orderId, items: activeSelections, override })
          setOverrideOpen(false)
          exitSelectMode()
        }}
      />
      <ItemConfigDialog
        open={!!configuringItem}
        item={configuringItem}
        onOpenChange={(open) => !open && setConfiguringItem(null)}
        onConfirm={handleConfigConfirm}
        pending={addItem.isPending}
      />
      <ItemConfigDialog
        open={!!editingItem}
        item={editingMenuItem ?? null}
        onOpenChange={(open) => !open && setEditingItem(null)}
        onConfirm={handleEditConfirm}
        pending={updateItem.isPending}
        title={editingItem ? `Edit ${editingItem.menuItemName}` : undefined}
        confirmLabel="Save Changes"
        initial={
          editingItem
            ? {
                qty: editingItem.qty,
                notes: editingItem.notes,
                modifierIds: editingItem.modifiers.map((m) => m.modifierId),
                fireCourse: editingItem.fireCourse,
              }
            : undefined
        }
      />
    </div>
  )
}
