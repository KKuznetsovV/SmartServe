'use client'

import { useEffect, useRef, useState } from 'react'
import { MoreVertical } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'

interface Props {
  canCancel: boolean
  cancelPending: boolean
  onCancel: () => Promise<void>
}

export function OrderOverflowMenu({ canCancel, cancelPending, onCancel }: Props) {
  const t = useTranslations('orderDetail')
  const tCommon = useTranslations('common')
  const [menuOpen, setMenuOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const rootRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    const close = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }
    window.addEventListener('mousedown', close)
    return () => window.removeEventListener('mousedown', close)
  }, [menuOpen])

  if (!canCancel) return null

  return (
    <div ref={rootRef} className="relative">
      <Button
        type="button"
        variant="outline"
        className="h-12 min-h-12 min-w-12"
        aria-haspopup="menu"
        aria-expanded={menuOpen}
        aria-label={t('moreActions')}
        data-testid="order-overflow"
        onClick={() => setMenuOpen((open) => !open)}
      >
        <MoreVertical className="h-5 w-5" />
      </Button>
      {menuOpen && (
        <div
          role="menu"
          className="absolute end-0 z-20 mt-1 min-w-44 rounded-md border bg-card py-1 shadow-md"
        >
          <button
            type="button"
            role="menuitem"
            className="flex min-h-12 w-full items-center px-4 text-start text-sm text-destructive hover:bg-muted"
            onClick={() => {
              setMenuOpen(false)
              setConfirmOpen(true)
            }}
          >
            {t('cancelOrder')}
          </button>
        </div>
      )}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('cancelOrder')}</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">{t('cancelOrderConfirm')}</p>
          <div className="mt-4 flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              className="min-h-12"
              onClick={() => setConfirmOpen(false)}
            >
              {tCommon('cancel')}
            </Button>
            <Button
              type="button"
              variant="destructive"
              className="min-h-12"
              disabled={cancelPending}
              data-testid="confirm-cancel-order"
              onClick={async () => {
                await onCancel()
                setConfirmOpen(false)
              }}
            >
              {t('cancelOrder')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
