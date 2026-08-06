'use client'

import { useEffect, useState } from 'react'
import { useSplitOrder } from '@/hooks/use-orders'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select } from '@/components/ui/select'
import { formatPrice } from '@/lib/utils'
import type { Order } from '@smartserve/types'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  order: Order
  onSplit?: () => void
}

export function SplitOrderDialog({ open, onOpenChange, order, onSplit }: Props) {
  const maxGuests = Math.max(order.guestCount ?? 2, 2)
  const guestOptions = Array.from({ length: maxGuests }, (_, i) => i + 1)
  const [assignments, setAssignments] = useState<Record<string, number>>({})
  const splitOrder = useSplitOrder()

  useEffect(() => {
    if (open) {
      setAssignments(Object.fromEntries(order.items.map((item) => [item.id, 1])))
    }
  }, [open, order.items])

  const distinctGuests = new Set(Object.values(assignments)).size
  const canSplit = distinctGuests >= 2

  async function handleConfirm() {
    if (!canSplit) return
    await splitOrder.mutateAsync({
      orderId: order.id,
      assignments: Object.entries(assignments).map(([itemId, guestNumber]) => ({ itemId, guestNumber })),
    })
    onOpenChange(false)
    onSplit?.()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Split Order Between Guests</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Assign every item to a guest. Each guest becomes a separate order with its own kitchen
            ticket and payment.
          </p>
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {order.items.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium truncate">
                    {item.qty}× {item.menuItemName}
                  </p>
                  <p className="text-xs text-muted-foreground">{formatPrice(item.unitPrice * item.qty)}</p>
                </div>
                <Select
                  className="w-28"
                  value={String(assignments[item.id] ?? 1)}
                  onChange={(e) =>
                    setAssignments((prev) => ({ ...prev, [item.id]: Number(e.target.value) }))
                  }
                >
                  {guestOptions.map((g) => (
                    <option key={g} value={g}>
                      Guest {g}
                    </option>
                  ))}
                </Select>
              </div>
            ))}
          </div>
          {!canSplit && (
            <p className="text-xs text-destructive">Assign items to at least two different guests.</p>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={handleConfirm} disabled={!canSplit || splitOrder.isPending}>
              Split Order
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
