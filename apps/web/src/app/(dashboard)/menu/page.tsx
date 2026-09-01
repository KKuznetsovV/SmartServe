'use client'

import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Search, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose } from '@/components/ui/dialog'
import { Spinner } from '@/components/ui/spinner'
import { useAuthStore } from '@/lib/auth-store'
import {
  useCategories,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
  useAllMenuItems,
} from '@/hooks/use-menu'
import { CategoryNode } from '@/components/menu/category-node'
import { ItemFormDialog } from '@/components/menu/item-form-dialog'
import { TrashDialog } from '@/components/menu/trash-dialog'
import type { MenuCategory, MenuItem } from '@smartserve/types'

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  nameHe: z.string().optional(),
  parentId: z.string().optional(),
})
type FormData = z.infer<typeof schema>

/** Ids of a category's descendants, so it can't be re-parented under one of its own children. */
function getDescendantIds(categories: MenuCategory[], id: string): Set<string> {
  const result = new Set<string>()
  const stack = [id]
  while (stack.length > 0) {
    const current = stack.pop()!
    for (const c of categories) {
      if (c.parentId === current && !result.has(c.id)) {
        result.add(c.id)
        stack.push(c.id)
      }
    }
  }
  return result
}

export default function MenuPage() {
  const activeLocationId = useAuthStore((s) => s.activeLocationId)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<MenuCategory | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  const [itemDialogOpen, setItemDialogOpen] = useState(false)
  const [itemDialogCategoryId, setItemDialogCategoryId] = useState<string | null>(null)
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null)
  const [trashDialogOpen, setTrashDialogOpen] = useState(false)

  const { data: categories = [], isLoading } = useCategories(activeLocationId)
  const createCategory = useCreateCategory()
  const updateCategory = useUpdateCategory()
  const deleteCategory = useDeleteCategory()

  const query = search.trim().toLowerCase()
  const { data: allItems } = useAllMenuItems(activeLocationId, query.length > 0)

  const matchingItemIds = useMemo(() => {
    if (!query || !allItems) return null
    return new Set(
      allItems
        .filter(
          (item) =>
            item.name.toLowerCase().includes(query) || item.nameHe?.toLowerCase().includes(query),
        )
        .map((item) => item.id),
    )
  }, [query, allItems])

  /** Category ids that should be auto-expanded (and, for non-leaf ancestors, kept visible)
   * because they, or one of their descendants, match the typed search. */
  const forceExpandIds = useMemo(() => {
    if (!query) return null
    const byId = new Map(categories.map((c) => [c.id, c]))
    const ids = new Set<string>()

    for (const c of categories) {
      if (c.name.toLowerCase().includes(query) || c.nameHe?.toLowerCase().includes(query)) {
        ids.add(c.id)
      }
    }
    if (allItems) {
      for (const item of allItems) {
        if (matchingItemIds?.has(item.id)) ids.add(item.categoryId)
      }
    }

    const withAncestors = new Set(ids)
    for (const id of ids) {
      let current = byId.get(id)
      while (current?.parentId) {
        withAncestors.add(current.parentId)
        current = byId.get(current.parentId)
      }
    }
    return withAncestors
  }, [query, categories, allItems, matchingItemIds])

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const topLevelCategories = categories
    .filter((c) => !c.parentId)
    .filter((c) => !query || forceExpandIds?.has(c.id))

  const openCreate = () => {
    setEditing(null)
    reset({ name: '', nameHe: '', parentId: '' })
    setDialogOpen(true)
  }

  const openEdit = (cat: MenuCategory) => {
    setEditing(cat)
    reset({ name: cat.name, nameHe: cat.nameHe ?? '', parentId: cat.parentId ?? '' })
    setDialogOpen(true)
  }

  const onSubmit = async (data: FormData) => {
    if (!activeLocationId) return
    if (editing) {
      await updateCategory.mutateAsync({
        id: editing.id,
        data: { name: data.name, nameHe: data.nameHe || undefined, parentId: data.parentId || undefined },
      })
    } else {
      await createCategory.mutateAsync({
        locationId: activeLocationId,
        name: data.name,
        nameHe: data.nameHe || undefined,
        parentId: data.parentId || undefined,
        sortOrder: categories.length,
        active: true,
      })
    }
    setDialogOpen(false)
    reset()
  }

  const handleDelete = async (id: string) => {
    setDeletingId(id)
    await deleteCategory.mutateAsync(id)
    setDeletingId(null)
  }

  const openAddItem = (categoryId: string) => {
    setEditingItem(null)
    setItemDialogCategoryId(categoryId)
    setItemDialogOpen(true)
  }

  const openEditItem = (item: MenuItem) => {
    setEditingItem(item)
    setItemDialogCategoryId(item.categoryId)
    setItemDialogOpen(true)
  }

  const excludedParentIds = editing ? getDescendantIds(categories, editing.id).add(editing.id) : new Set<string>()

  if (!activeLocationId) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground">No location selected. Please contact your administrator.</p>
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Menu Management</h1>
          <p className="text-sm text-muted-foreground">Manage categories and menu items</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setTrashDialogOpen(true)}>
            <Trash2 className="mr-1 h-4 w-4" />
            View Trash
          </Button>
          <Button onClick={openCreate}>
            <Plus className="mr-1 h-4 w-4" />
            Add Category
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="mb-4 max-w-sm space-y-1">
        <Label htmlFor="menu-search">Search menu items</Label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="menu-search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by item name…"
            className="pl-8"
            aria-label="Search menu items by name"
          />
        </div>
      </div>

      {/* Category tree */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : categories.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
          <p className="mb-4 text-muted-foreground">No categories yet</p>
          <Button variant="outline" onClick={openCreate}>
            <Plus className="mr-1 h-4 w-4" />
            Create your first category
          </Button>
        </div>
      ) : query && topLevelCategories.length === 0 ? (
        <p className="text-muted-foreground" role="status" aria-live="polite">
          No menu items match &quot;{search}&quot;.
        </p>
      ) : (
        <div className="space-y-2">
          {query && (
            <p className="text-sm text-muted-foreground" role="status" aria-live="polite">
              {matchingItemIds?.size ?? 0} item{(matchingItemIds?.size ?? 0) !== 1 ? 's' : ''} match &quot;{search}&quot;
            </p>
          )}
          {topLevelCategories.map((cat) => (
            <CategoryNode
              key={cat.id}
              category={cat}
              categories={categories}
              onEdit={openEdit}
              onDelete={handleDelete}
              deletingId={deletingId}
              searchQuery={query}
              matchingItemIds={matchingItemIds}
              forceExpandIds={forceExpandIds}
              onAddItem={openAddItem}
              onEditItem={openEditItem}
            />
          ))}
        </div>
      )}

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit Category' : 'New Category'}</DialogTitle>
            <DialogClose onClose={() => setDialogOpen(false)} />
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="name">Name (English)</Label>
              <Input id="name" {...register('name')} placeholder="e.g. Starters" />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="nameHe">Name (Hebrew)</Label>
              <Input id="nameHe" {...register('nameHe')} placeholder="e.g. מנות ראשונות" dir="rtl" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="parentId">Parent category (optional)</Label>
              <Select id="parentId" {...register('parentId')}>
                <option value="">None (top-level category)</option>
                {categories
                  .filter((c) => !excludedParentIds.has(c.id))
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
              </Select>
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createCategory.isPending || updateCategory.isPending}
              >
                {(createCategory.isPending || updateCategory.isPending) && (
                  <Spinner className="mr-2 h-4 w-4" />
                )}
                {editing ? 'Save Changes' : 'Create'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <ItemFormDialog
        open={itemDialogOpen}
        onOpenChange={setItemDialogOpen}
        categoryId={itemDialogCategoryId}
        editing={editingItem}
      />

      <TrashDialog open={trashDialogOpen} onOpenChange={setTrashDialogOpen} locationId={activeLocationId} />
    </div>
  )
}
