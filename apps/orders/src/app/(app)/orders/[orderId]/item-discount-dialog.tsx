'use client'

import { useState } from 'react'
import { useApplyItemDiscount } from '@/hooks/use-orders'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import type { ItemSelection } from '@smartserve/api-client'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  orderId: string
  items: ItemSelection[]
  onDone?: () => void
}

/** Applies (or clears) a manual per-item discount — distinct from the order-level discount
 * code feature; this is a manager/waiter-entered %/fixed reduction on specific line items. */
export function ItemDiscountDialog({ open, onOpenChange, orderId, items, onDone }: Props) {
  const [discountType, setDiscountType] = useState<'percent' | 'fixed'>('percent')
  const [value, setValue] = useState('')
  const applyItemDiscount = useApplyItemDiscount()

  async function handleApply() {
    const parsed = Number(value)
    if (!value.trim() || Number.isNaN(parsed) || parsed <= 0) return
    await applyItemDiscount.mutateAsync({ orderId, items, discountType, discountValue: parsed })
    onOpenChange(false)
    setValue('')
    onDone?.()
  }

  async function handleClear() {
    await applyItemDiscount.mutateAsync({ orderId, items, discountType: null, discountValue: null })
    onOpenChange(false)
    setValue('')
    onDone?.()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Discount Item{items.length === 1 ? '' : 's'}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Applies to {items.length} selected item{items.length === 1 ? '' : 's'}.
          </p>
          <div className="flex gap-2">
            <Button
              type="button"
              variant={discountType === 'percent' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setDiscountType('percent')}
            >
              Percent %
            </Button>
            <Button
              type="button"
              variant={discountType === 'fixed' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setDiscountType('fixed')}
            >
              Fixed ₪
            </Button>
          </div>
          <Input
            type="number"
            min={0}
            placeholder={discountType === 'percent' ? 'e.g. 10 (%)' : 'e.g. 20 (₪)'}
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
          <div className="flex justify-between gap-2 pt-2">
            <Button variant="outline" onClick={handleClear} disabled={applyItemDiscount.isPending}>
              Clear Discount
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button onClick={handleApply} disabled={applyItemDiscount.isPending || !value.trim()}>
                Apply
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
