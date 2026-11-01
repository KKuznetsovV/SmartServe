'use client'

import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { GripVertical, Pencil } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { cn, formatPrice, getItemLineTotal } from '@/lib/utils'
import type { OrderItem } from '@smartserve/types'

const STATUS_VARIANT: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  held: 'secondary',
  pending: 'outline',
  preparing: 'secondary',
  ready: 'default',
  served: 'default',
  cancelled: 'destructive',
}

interface Props {
  item: OrderItem
  /** Open tickets have not been sent; pending there means "not sent", not kitchen pending. */
  orderStatus: string
  /** Whether drag-to-reorder / drag-out-to-cancel is enabled (order is still open/submitted). */
  draggable: boolean
  /** Called when the edit (pencil) button is tapped — omit to hide the button entirely. */
  onEdit?: (item: OrderItem) => void
  /** When set, a checkbox is shown instead of the drag handle for the multi-select action toolbar. */
  selectable?: boolean
  selected?: boolean
  onToggleSelect?: (itemId: string) => void
}

/** A single order item row: drag the handle to reorder, or drag it onto the cancel zone to remove it. */
export function OrderItemRow({
  item,
  orderStatus,
  draggable,
  onEdit,
  selectable,
  selected,
  onToggleSelect,
}: Props) {
  const t = useTranslations('orderItemRow')
  const tItemStatus = useTranslations('itemStatus')
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: item.id,
    data: { type: 'order-item' as const, item },
    disabled: !draggable || selectable,
  })

  const canEdit = draggable && !selectable && !['served', 'cancelled'].includes(item.status)
  const lineTotal = getItemLineTotal(item)
  const unsent = orderStatus === 'open' && item.status === 'pending'
  const statusLabel = unsent ? tItemStatus('notSent') : tItemStatus(item.status)

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        'flex items-start justify-between gap-2 border-b bg-card py-2 last:border-0',
        isDragging && 'opacity-40',
      )}
    >
      <div className="flex items-start gap-2">
        {selectable ? (
          <Checkbox
            className="mt-0.5"
            checked={!!selected}
            onCheckedChange={() => onToggleSelect?.(item.id)}
            aria-label={t('selectItem')}
          />
        ) : (
          draggable && (
            <button
              type="button"
              {...attributes}
              {...listeners}
              className="mt-0.5 flex h-12 min-h-12 w-12 min-w-12 touch-none items-center justify-center text-muted-foreground hover:text-foreground active:cursor-grabbing"
              aria-label={t('dragToReorder')}
            >
              <GripVertical className="h-4 w-4" />
            </button>
          )
        )}
        <div className="space-y-0.5">
          <p className="text-sm font-medium">
            {item.qty}× {item.menuItemName}
          </p>
          {item.modifiers.length > 0 && (
            <p className="text-xs text-muted-foreground">{item.modifiers.map((m) => m.name).join(', ')}</p>
          )}
          {item.notes && <p className="text-xs italic text-muted-foreground">{item.notes}</p>}
          <div className="flex items-center gap-1 flex-wrap">
            <Badge variant={STATUS_VARIANT[item.status] ?? 'outline'} className="text-xs capitalize">
              {statusLabel}
            </Badge>
            {item.fireCourse > 1 && (
              <Badge variant="outline" className="text-xs">
                {t('course', { n: item.fireCourse })}
              </Badge>
            )}
            {item.guestNumber != null && (
              <Badge variant="outline" className="text-xs">
                {t('guest', { n: item.guestNumber })}
              </Badge>
            )}
            {item.isComped && (
              <Badge variant="secondary" className="text-xs">
                {t('onTheHouse')}
              </Badge>
            )}
            {!item.isComped && item.discountAmount > 0 && (
              <Badge variant="secondary" className="text-xs">
                {t('discount', { amount: formatPrice(item.discountAmount) })}
              </Badge>
            )}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {canEdit && onEdit && (
          <button
            type="button"
            onClick={() => onEdit(item)}
            className="flex h-12 min-h-12 w-12 min-w-12 items-center justify-center text-muted-foreground hover:text-foreground"
            aria-label={t('editItem')}
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
        )}
        {item.isComped || item.discountAmount > 0 ? (
          <div className="text-end">
            <span className="block text-xs text-muted-foreground line-through">
              {formatPrice(item.unitPrice * item.qty)}
            </span>
            <span className="whitespace-nowrap text-sm font-medium">{formatPrice(lineTotal)}</span>
          </div>
        ) : (
          <span className="whitespace-nowrap text-sm font-medium">{formatPrice(lineTotal)}</span>
        )}
      </div>
    </div>
  )
}

/** Floating clone rendered inside DragOverlay while an order item row is being dragged. */
export function OrderItemRowPreview({ item }: { item: OrderItem }) {
  return (
    <div className="w-64 rounded-md border bg-card px-3 py-2 shadow-lg">
      <p className="text-sm font-medium">
        {item.qty}× {item.menuItemName}
      </p>
    </div>
  )
}
