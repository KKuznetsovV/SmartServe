'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Trash2 } from 'lucide-react'
import { useTranslations } from 'next-intl'
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
  const t = useTranslations('menu')
  const tCommon = useTranslations('common')
  const activeLocationId = useAuthStore((s) => s.activeLocationId)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<MenuCategory | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const [itemDialogOpen, setItemDialogOpen] = useState(false)
  const [itemDialogCategoryId, setItemDialogCategoryId] = useState<string | null>(null)
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null)
  const [trashDialogOpen, setTrashDialogOpen] = useState(false)

  const { data: categories = [], isLoading } = useCategories(activeLocationId)
  const createCategory = useCreateCategory()
  const updateCategory = useUpdateCategory()
  const deleteCategory = useDeleteCategory()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const topLevelCategories = categories.filter((c) => !c.parentId)

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
        <p className="text-muted-foreground">{t('noLocationSelected')}</p>
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t('title')}</h1>
          <p className="text-sm text-muted-foreground">{t('subtitle')}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setTrashDialogOpen(true)}>
            <Trash2 className="me-1 h-4 w-4" />
            {t('viewTrash')}
          </Button>
          <Button onClick={openCreate}>
            <Plus className="me-1 h-4 w-4" />
            {t('addCategory')}
          </Button>
        </div>
      </div>

      {/* Category tree */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : categories.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
          <p className="mb-4 text-muted-foreground">{t('noCategories')}</p>
          <Button variant="outline" onClick={openCreate}>
            <Plus className="me-1 h-4 w-4" />
            {t('createFirstCategory')}
          </Button>
        </div>
      ) : (
        <div className="space-y-2">
          {topLevelCategories.map((cat) => (
            <CategoryNode
              key={cat.id}
              category={cat}
              categories={categories}
              onEdit={openEdit}
              onDelete={handleDelete}
              deletingId={deletingId}
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
            <DialogTitle>{editing ? t('editCategory') : t('newCategory')}</DialogTitle>
            <DialogClose onClose={() => setDialogOpen(false)} />
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="name">{t('nameEnglish')}</Label>
              <Input id="name" {...register('name')} placeholder="e.g. Starters" />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="nameHe">{t('nameHebrew')}</Label>
              <Input id="nameHe" {...register('nameHe')} placeholder="e.g. מנות ראשונות" dir="rtl" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="parentId">{t('parentCategory')}</Label>
              <Select id="parentId" {...register('parentId')}>
                <option value="">{t('noneTopLevel')}</option>
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
                {tCommon('cancel')}
              </Button>
              <Button
                type="submit"
                disabled={createCategory.isPending || updateCategory.isPending}
              >
                {(createCategory.isPending || updateCategory.isPending) && (
                  <Spinner className="me-2 h-4 w-4" />
                )}
                {editing ? t('saveChanges') : t('create')}
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
