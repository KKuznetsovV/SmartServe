'use client'

import { useDroppable } from '@dnd-kit/core'
import { Trash2 } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { cn } from '@/lib/utils'

/** Floating drop target that appears while dragging an order item out to remove/cancel it. */
export function CancelDropZone({ visible, mode }: { visible: boolean; mode: 'remove' | 'cancel' }) {
  const { setNodeRef, isOver } = useDroppable({ id: 'cancel-zone' })
  const t = useTranslations('cancelDropZone')

  return (
    <div
      ref={setNodeRef}
      className={cn(
        'fixed inset-x-0 bottom-6 z-50 mx-auto flex w-fit items-center gap-2 rounded-full border-2 border-dashed px-6 py-3 text-sm font-medium shadow-lg transition-all',
        visible ? 'opacity-100' : 'pointer-events-none opacity-0',
        isOver
          ? 'border-destructive bg-destructive text-destructive-foreground'
          : 'border-destructive/50 bg-background text-destructive',
      )}
    >
      <Trash2 className="h-4 w-4" />
      {mode === 'remove' ? t('dropToRemove') : t('dropToCancel')}
    </div>
  )
}
