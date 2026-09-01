'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
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
  const t = useTranslations('itemDiscountDialog')
  const tCommon = useTranslations('common')
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
          <DialogTitle>{t('title', { count: items.length })}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">{t('appliesHint', { count: items.length })}</p>
          <div className="flex gap-2">
            <Button
              type="button"
              variant={discountType === 'percent' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setDiscountType('percent')}
            >
              {t('percent')}
            </Button>
            <Button
              type="button"
              variant={discountType === 'fixed' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setDiscountType('fixed')}
            >
              {t('fixed')}
            </Button>
          </div>
          <Input
            type="number"
            min={0}
            placeholder={discountType === 'percent' ? t('percentPlaceholder') : t('fixedPlaceholder')}
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
          <div className="flex justify-between gap-2 pt-2">
            <Button variant="outline" onClick={handleClear} disabled={applyItemDiscount.isPending}>
              {t('clearDiscount')}
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                {tCommon('cancel')}
              </Button>
              <Button onClick={handleApply} disabled={applyItemDiscount.isPending || !value.trim()}>
                {tCommon('apply')}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
