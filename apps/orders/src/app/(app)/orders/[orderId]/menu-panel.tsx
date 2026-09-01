'use client'

import { useEffect, useMemo, useState } from 'react'
import { useDraggable } from '@dnd-kit/core'
import { GlassWater, UtensilsCrossed } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { useCategories, useMenuItems } from '@/hooks/use-menu'
import { Spinner } from '@/components/ui/spinner'
import { formatPrice } from '@/lib/utils'
import type { MenuItem } from '@smartserve/types'

interface Props {
  locationId: string
  onItemTap: (item: MenuItem) => void
}

/** Menu browser: two top-level branches (e.g. Food/Drinks) → subcategories → draggable/tappable item cards. */
export function MenuPanel({ locationId, onItemTap }: Props) {
  const t = useTranslations('menuPanel')
  const { data: categories, isLoading: categoriesLoading } = useCategories(locationId)

  const roots = useMemo(
    () => (categories ?? []).filter((c) => !c.parentId).sort((a, b) => a.sortOrder - b.sortOrder),
    [categories],
  )
  const [activeRootId, setActiveRootId] = useState<string | null>(null)

  useEffect(() => {
    if (!activeRootId && roots.length > 0) setActiveRootId(roots[0].id)
  }, [roots, activeRootId])

  const children = useMemo(
    () => (categories ?? []).filter((c) => c.parentId === activeRootId).sort((a, b) => a.sortOrder - b.sortOrder),
    [categories, activeRootId],
  )
  const [activeCategoryId, setActiveCategoryId] = useState<string | null>(null)

  useEffect(() => {
    // switching branch defaults to its first subcategory (or the branch itself if it has none)
    setActiveCategoryId(children[0]?.id ?? activeRootId)
  }, [activeRootId, children])

  const { data: items, isLoading: itemsLoading } = useMenuItems(activeCategoryId)
  const availableItems = (items ?? []).filter((i) => i.active && i.inStock)

  if (categoriesLoading) {
    return (
      <div className="flex items-center justify-center rounded-lg border p-16">
        <Spinner />
      </div>
    )
  }

  if (roots.length === 0) {
    return (
      <div className="rounded-lg border p-8 text-center text-sm text-muted-foreground">
        {t('noCategories')}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {roots.map((root) => {
          const Icon = /drink/i.test(root.name) ? GlassWater : UtensilsCrossed
          return (
            <button
              key={root.id}
              type="button"
              onClick={() => setActiveRootId(root.id)}
              className={`flex flex-1 items-center justify-center gap-2 rounded-lg border px-4 py-3 text-sm font-semibold transition-colors sm:flex-none sm:px-6 ${
                activeRootId === root.id
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border bg-card hover:bg-muted'
              }`}
            >
              <Icon className="h-4 w-4" />
              {root.name}
            </button>
          )
        })}
      </div>

      {children.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {children.map((cat) => (
            <button
              key={cat.id}
              type="button"
              onClick={() => setActiveCategoryId(cat.id)}
              className={`rounded-full border px-3.5 py-1.5 text-sm transition-colors ${
                activeCategoryId === cat.id
                  ? 'border-primary bg-primary/10 font-medium text-primary'
                  : 'border-border hover:bg-muted'
              }`}
            >
              {cat.name}
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 xl:grid-cols-4">
        {itemsLoading && (
          <div className="col-span-full flex justify-center py-8">
            <Spinner />
          </div>
        )}
        {!itemsLoading &&
          availableItems.map((item) => (
            <DraggableItemCard key={item.id} item={item} onTap={() => onItemTap(item)} />
          ))}
        {!itemsLoading && availableItems.length === 0 && (
          <p className="col-span-full py-8 text-center text-sm text-muted-foreground">{t('noAvailableItems')}</p>
        )}
      </div>
    </div>
  )
}

function DraggableItemCard({ item, onTap }: { item: MenuItem; onTap: () => void }) {
  const t = useTranslations('menuPanel')
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `menu-item-${item.id}`,
    data: { type: 'menu-item' as const, item },
  })

  return (
    <button
      ref={setNodeRef}
      type="button"
      onClick={onTap}
      {...listeners}
      {...attributes}
      className={`touch-none select-none rounded-lg border bg-card p-3 text-start shadow-sm transition-shadow hover:shadow-md active:cursor-grabbing ${
        isDragging ? 'opacity-40' : ''
      }`}
    >
      <p className="text-sm font-medium leading-tight">{item.name}</p>
      <p className="mt-1 text-sm font-semibold text-primary">{formatPrice(item.price)}</p>
      {item.modifierGroups.length > 0 && (
        <p className="mt-1 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">{t('customizable')}</p>
      )}
    </button>
  )
}

/** Floating clone rendered inside DragOverlay while a menu item card is being dragged. */
export function MenuItemCardPreview({ item }: { item: MenuItem }) {
  return (
    <div className="w-40 cursor-grabbing rounded-lg border bg-card p-3 text-start shadow-lg">
      <p className="text-sm font-medium leading-tight">{item.name}</p>
      <p className="mt-1 text-sm font-semibold text-primary">{formatPrice(item.price)}</p>
    </div>
  )
}
