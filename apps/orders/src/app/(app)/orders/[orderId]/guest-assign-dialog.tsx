'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { useAssignGuests } from '@/hooks/use-orders'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import type { ItemSelection } from '@smartserve/api-client'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  orderId: string
  items: ItemSelection[]
  guestCount: number
  onDone?: () => void
}

/** Tags the selected items with a guest number, in place — never creates a new order.
 * This is purely organizational (e.g. so a table can later be paid per-guest); it is
 * entirely optional and only some items on an order need to be tagged. */
export function GuestAssignDialog({ open, onOpenChange, orderId, items, guestCount, onDone }: Props) {
  const t = useTranslations('guestAssignDialog')
  const tCommon = useTranslations('common')
  const [guestNumber, setGuestNumber] = useState<number | null>(1)
  const assignGuests = useAssignGuests()
  const guestOptions = Array.from({ length: Math.max(guestCount, 2) }, (_, i) => i + 1)

  async function handleConfirm() {
    await assignGuests.mutateAsync({
      orderId,
      assignments: items.map((item) => ({ ...item, guestNumber })),
    })
    onOpenChange(false)
    onDone?.()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('title')}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">{t('tagHint', { count: items.length })}</p>
          <div className="flex flex-wrap gap-2">
            {guestOptions.map((g) => (
              <Button
                key={g}
                type="button"
                variant={guestNumber === g ? 'default' : 'outline'}
                size="sm"
                onClick={() => setGuestNumber(g)}
              >
                {t('guest', { number: g })}
              </Button>
            ))}
            <Button
              type="button"
              variant={guestNumber === null ? 'default' : 'outline'}
              size="sm"
              onClick={() => setGuestNumber(null)}
            >
              {t('sharedClear')}
            </Button>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              {tCommon('cancel')}
            </Button>
            <Button onClick={handleConfirm} disabled={assignGuests.isPending}>
              {tCommon('apply')}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
