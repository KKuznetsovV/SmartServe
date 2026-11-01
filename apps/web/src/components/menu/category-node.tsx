'use client'

import { useState } from 'react'
import { ChevronRight, ChevronDown, Pencil, Trash2, Plus, GripVertical } from 'lucide-react'
import { useLocale, useTranslations } from 'next-intl'
import { localizedName } from '@smartserve/ui'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'
import { useMenuItems, useUpdateMenuItem, useReorderMenuItems } from '@/hooks/use-menu'
import { ItemCard } from '@/components/menu/item-card'
import type { MenuCategory, MenuItem } from '@smartserve/types'

const ITEM_DRAG_TYPE = 'application/x-smartserve-item'

interface ItemDragPayload {
  itemId: string
  categoryId: string
}

export function CategoryNode({
  category,
  categories,
  onEdit,
  onDelete,
  deletingId,
  onAddItem,
  onEditItem,
}: {
  category: MenuCategory
  categories: MenuCategory[]
  onEdit: (cat: MenuCategory) => void
  onDelete: (id: string) => void
  deletingId: string | null
  onAddItem: (categoryId: string) => void
  onEditItem: (item: MenuItem) => void
}) {
  const t = useTranslations('menu')
  const locale = useLocale()
  const [expanded, setExpanded] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const children = categories.filter((c) => c.parentId === category.id)
  const { data: items = [], isLoading: itemsLoading } = useMenuItems(category.id, expanded)
  const updateItem = useUpdateMenuItem()
  const reorderItems = useReorderMenuItems()

  const readDragPayload = (e: React.DragEvent): ItemDragPayload | null => {
    const raw = e.dataTransfer.getData(ITEM_DRAG_TYPE)
    if (!raw) return null
    try {
      return JSON.parse(raw) as ItemDragPayload
    } catch {
      return null
    }
  }

  /** Drop an item at `targetItemId`'s position (or at the end, if null) within this category. */
  const handleItemDrop = async (e: React.DragEvent, targetItemId: string | null) => {
    e.preventDefault()
    e.stopPropagation()
    setDragOver(false)
    const dragged = readDragPayload(e)
    if (!dragged || dragged.itemId === targetItemId) return

    const sameCategory = dragged.categoryId === category.id
    const ids = items.map((i) => i.id).filter((id) => id !== dragged.itemId)
    const insertAt = targetItemId ? ids.indexOf(targetItemId) : ids.length
    ids.splice(insertAt === -1 ? ids.length : insertAt, 0, dragged.itemId)

    if (!sameCategory) {
      await updateItem.mutateAsync({
        id: dragged.itemId,
        data: { categoryId: category.id },
        oldCategoryId: dragged.categoryId,
      })
    }
    await reorderItems.mutateAsync({ categoryId: category.id, ids })
  }

  return (
    <div>
      <Card
        className={`group cursor-pointer transition-shadow hover:shadow-md ${dragOver ? 'ring-2 ring-primary' : ''}`}
        onClick={() => setExpanded((v) => !v)}
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => handleItemDrop(e, null)}
      >
        <CardContent className="flex items-center justify-between p-4">
          <div className="flex min-w-0 flex-1 items-center gap-2">
            {expanded ? (
              <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground rtl:-scale-x-100" />
            )}
            <span className="font-medium truncate">{localizedName(category, locale)}</span>
            <Badge variant={category.active ? 'success' : 'secondary'}>
              {category.active ? t('active') : t('hidden')}
            </Badge>
          </div>
          <div className="flex shrink-0 items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="icon"
              aria-label={t('editCategory')}
              onClick={(e) => { e.stopPropagation(); onEdit(category) }}
            >
              <Pencil className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              aria-label={t('deleteCategory')}
              onClick={(e) => { e.stopPropagation(); onDelete(category.id) }}
              disabled={deletingId === category.id}
            >
              {deletingId === category.id ? (
                <Spinner className="h-4 w-4" />
              ) : (
                <Trash2 className="h-4 w-4 text-destructive" />
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {expanded && (
        <div className="ms-6 mt-2 space-y-2 border-s-2 ps-4">
          {children.length > 0 && (
            <div className="space-y-2">
              {children.map((child) => (
                <CategoryNode
                  key={child.id}
                  category={child}
                  categories={categories}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  deletingId={deletingId}
                  onAddItem={onAddItem}
                  onEditItem={onEditItem}
                />
              ))}
            </div>
          )}

          {itemsLoading ? (
            <div className="flex justify-center py-4">
              <Spinner />
            </div>
          ) : items.length > 0 ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {items.map((item) => (
                <div
                  key={item.id}
                  className="flex items-start gap-1"
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => handleItemDrop(e, item.id)}
                >
                  <div
                    draggable
                    onDragStart={(e) => {
                      const payload: ItemDragPayload = { itemId: item.id, categoryId: category.id }
                      e.dataTransfer.setData(ITEM_DRAG_TYPE, JSON.stringify(payload))
                      e.dataTransfer.effectAllowed = 'move'
                    }}
                    className="mt-2 shrink-0 cursor-grab touch-none text-muted-foreground hover:text-foreground active:cursor-grabbing"
                    title={t('dragToReorderHint')}
                  >
                    <GripVertical className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <ItemCard item={item} categoryId={category.id} onEdit={onEditItem} />
                  </div>
                </div>
              ))}
            </div>
          ) : null}

          <Button
            variant="outline"
            size="sm"
            onClick={(e) => { e.stopPropagation(); onAddItem(category.id) }}
          >
            <Plus className="me-1 h-3 w-3" />
            {t('addItem')}
          </Button>
        </div>
      )}
    </div>
  )
}
