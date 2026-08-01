'use client'

import { useState } from 'react'
import { ChevronRight, ChevronDown, Pencil, Trash2, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'
import { useMenuItems } from '@/hooks/use-menu'
import { ItemCard } from '@/components/menu/item-card'
import type { MenuCategory, MenuItem } from '@smartserve/types'

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
  const [expanded, setExpanded] = useState(false)
  const children = categories.filter((c) => c.parentId === category.id)
  const { data: items = [], isLoading: itemsLoading } = useMenuItems(category.id, expanded)

  return (
    <div>
      <Card
        className="group cursor-pointer transition-shadow hover:shadow-md"
        onClick={() => setExpanded((v) => !v)}
      >
        <CardContent className="flex items-center justify-between p-4">
          <div className="flex min-w-0 flex-1 items-center gap-2">
            {expanded ? (
              <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
            )}
            <span className="font-medium truncate">{category.name}</span>
            {category.nameHe && (
              <span className="text-sm text-muted-foreground dir-rtl">{category.nameHe}</span>
            )}
            <Badge variant={category.active ? 'success' : 'secondary'}>
              {category.active ? 'Active' : 'Hidden'}
            </Badge>
          </div>
          <div className="flex shrink-0 items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="icon"
              onClick={(e) => { e.stopPropagation(); onEdit(category) }}
            >
              <Pencil className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
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
        <div className="ml-6 mt-2 space-y-2 border-l-2 pl-4">
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
                <ItemCard key={item.id} item={item} categoryId={category.id} onEdit={onEditItem} />
              ))}
            </div>
          ) : null}

          <Button
            variant="outline"
            size="sm"
            onClick={(e) => { e.stopPropagation(); onAddItem(category.id) }}
          >
            <Plus className="mr-1 h-3 w-3" />
            Add Item
          </Button>
        </div>
      )}
    </div>
  )
}
