'use client'

import { useState } from 'react'
import { RotateCcw, Trash2 } from 'lucide-react'
import { useLocale, useTranslations } from 'next-intl'
import { localizedName } from '@smartserve/ui'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose } from '@/components/ui/dialog'
import { Spinner } from '@/components/ui/spinner'
import { formatPrice } from '@/lib/utils'
import { useTrashedItems, useRestoreMenuItem, usePermanentlyDeleteMenuItem } from '@/hooks/use-menu'

/** Manager-facing view of trashed (soft-deleted) menu items: restore them, or permanently
 * delete them one at a time. Automatic purge after a retention window isn't implemented yet
 * (needs job-scheduling infrastructure this codebase doesn't have) — see
 * docs/microservices-plan.md for the deferred-scope note; for now this dialog is the only
 * way an item leaves the trash for good. */
export function TrashDialog({
  open,
  onOpenChange,
  locationId,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  locationId: string
}) {
  const t = useTranslations('trash')
  const tCommon = useTranslations('common')
  const locale = useLocale()
  const { data: trashedItems = [], isLoading } = useTrashedItems(open ? locationId : null)
  const restoreItem = useRestoreMenuItem()
  const permanentlyDeleteItem = usePermanentlyDeleteMenuItem()
  const [confirmingId, setConfirmingId] = useState<string | null>(null)

  const handlePermanentDelete = async (id: string) => {
    await permanentlyDeleteItem.mutateAsync({ id, locationId })
    setConfirmingId(null)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{t('title')}</DialogTitle>
          <DialogClose onClose={() => onOpenChange(false)} />
        </DialogHeader>
        <div className="max-h-[60vh] space-y-2 overflow-y-auto">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Spinner />
            </div>
          ) : trashedItems.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">{t('empty')}</p>
          ) : (
            trashedItems.map((item) => (
              <Card key={item.id}>
                <CardContent className="flex items-center justify-between gap-2 p-3">
                  <div className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{localizedName(item, locale)}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatPrice(item.price)}
                      {item.deletedAt && ` · ${t('trashedOn', { date: new Date(item.deletedAt).toLocaleDateString() })}`}
                    </span>
                  </div>
                  {confirmingId === item.id ? (
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="text-xs text-destructive">{t('confirmDeleteForever')}</span>
                      <Button
                        size="sm"
                        variant="destructive"
                        disabled={permanentlyDeleteItem.isPending}
                        onClick={() => handlePermanentDelete(item.id)}
                      >
                        {permanentlyDeleteItem.isPending && <Spinner className="me-1 h-3 w-3" />}
                        {tCommon('confirm')}
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setConfirmingId(null)}>
                        {tCommon('cancel')}
                      </Button>
                    </div>
                  ) : (
                    <div className="flex shrink-0 items-center gap-1">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={restoreItem.isPending}
                        onClick={() => restoreItem.mutate({ id: item.id, locationId })}
                      >
                        <RotateCcw className="me-1 h-3 w-3" />
                        {t('restore')}
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        aria-label={t('permanentlyDelete')}
                        onClick={() => setConfirmingId(item.id)}
                        title={t('permanentlyDelete')}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
