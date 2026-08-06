'use client'

import { useState } from 'react'
import { useAssignGuests } from '@/hooks/use-orders'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  orderId: string
  itemIds: string[]
  guestCount: number
  onDone?: () => void
}

/** Tags the selected items with a guest number, in place — never creates a new order.
 * This is purely organizational (e.g. so a table can later be paid per-guest); it is
 * entirely optional and only some items on an order need to be tagged. */
export function GuestAssignDialog({ open, onOpenChange, orderId, itemIds, guestCount, onDone }: Props) {
  const [guestNumber, setGuestNumber] = useState<number | null>(1)
  const assignGuests = useAssignGuests()
  const guestOptions = Array.from({ length: Math.max(guestCount, 2) }, (_, i) => i + 1)

  async function handleConfirm() {
    await assignGuests.mutateAsync({
      orderId,
      assignments: itemIds.map((itemId) => ({ itemId, guestNumber })),
    })
    onOpenChange(false)
    onDone?.()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign to Guest</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Tag {itemIds.length} item{itemIds.length === 1 ? '' : 's'} with a guest number, or clear the tag
            to share it across the table again.
          </p>
          <div className="flex flex-wrap gap-2">
            {guestOptions.map((g) => (
              <Button
                key={g}
                type="button"
                variant={guestNumber === g ? 'default' : 'outline'}
                size="sm"
                onClick={() => setGuestNumber(g)}
              >
                Guest {g}
              </Button>
            ))}
            <Button
              type="button"
              variant={guestNumber === null ? 'default' : 'outline'}
              size="sm"
              onClick={() => setGuestNumber(null)}
            >
              Shared / Clear
            </Button>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={handleConfirm} disabled={assignGuests.isPending}>
              Apply
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
