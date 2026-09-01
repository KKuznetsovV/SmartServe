'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { formatPrice } from '@/lib/utils'
import type { OrderItem } from '@smartserve/types'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Only the selected items whose qty > 1 — items with qty 1 never need this prompt. */
  items: OrderItem[]
  onConfirm: (quantities: Record<string, number>) => void
}

/** Asks how many units of each multi-quantity selected item a bulk action (guest tag,
 * discount, comp, delete) should apply to — the rest of that line stays untouched. */
export function QuantitySelectDialog({ open, onOpenChange, items, onConfirm }: Props) {
  const t = useTranslations('quantitySelectDialog')
  const tCommon = useTranslations('common')
  const [quantities, setQuantities] = useState<Record<string, number>>({})

  function handleOpenChange(isOpen: boolean) {
    if (isOpen) {
      // Default each item to its full quantity so "Apply" with no edits behaves like before.
      setQuantities(Object.fromEntries(items.map((i) => [i.id, i.qty])))
    }
    onOpenChange(isOpen)
  }

  function setQty(itemId: string, qty: number, max: number) {
    setQuantities((prev) => ({ ...prev, [itemId]: Math.min(Math.max(qty, 1), max) }))
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('title')}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">{t('description')}</p>
          <div className="space-y-2">
            {items.map((item) => (
              <div key={item.id} className="flex items-center justify-between gap-3 border-b pb-2 last:border-0">
                <div>
                  <p className="text-sm font-medium">{item.menuItemName}</p>
                  <p className="text-xs text-muted-foreground">
                    {item.qty} {t('onOrder')} · {formatPrice(item.unitPrice)} {t('each')}
                  </p>
                </div>
                <Input
                  type="number"
                  min={1}
                  max={item.qty}
                  className="w-20"
                  value={quantities[item.id] ?? item.qty}
                  onChange={(e) => setQty(item.id, Number(e.target.value), item.qty)}
                />
              </div>
            ))}
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              {tCommon('cancel')}
            </Button>
            <Button onClick={() => onConfirm(quantities)}>{t('continue')}</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
