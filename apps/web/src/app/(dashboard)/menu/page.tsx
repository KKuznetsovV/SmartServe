'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Pencil, Trash2, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose } from '@/components/ui/dialog'
import { Spinner } from '@/components/ui/spinner'
import { useAuthStore } from '@/lib/auth-store'
import {
  useCategories,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
} from '@/hooks/use-menu'
import type { MenuCategory } from '@smartserve/types'

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  nameHe: z.string().optional(),
})
type FormData = z.infer<typeof schema>

export default function MenuPage() {
  const router = useRouter()
  const activeLocationId = useAuthStore((s) => s.activeLocationId)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<MenuCategory | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

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

  const openCreate = () => {
    setEditing(null)
    reset({ name: '', nameHe: '' })
    setDialogOpen(true)
  }

  const openEdit = (cat: MenuCategory) => {
    setEditing(cat)
    reset({ name: cat.name, nameHe: cat.nameHe ?? '' })
    setDialogOpen(true)
  }

  const onSubmit = async (data: FormData) => {
    if (!activeLocationId) return
    if (editing) {
      await updateCategory.mutateAsync({ id: editing.id, data: { name: data.name, nameHe: data.nameHe || undefined } })
    } else {
      await createCategory.mutateAsync({
        locationId: activeLocationId,
        name: data.name,
        nameHe: data.nameHe || undefined,
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
        <Button onClick={openCreate}>
          <Plus className="mr-1 h-4 w-4" />
          Add Category
        </Button>
      </div>

      {/* Categories */}
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
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {categories.map((cat) => (
            <Card
              key={cat.id}
              className="group cursor-pointer transition-shadow hover:shadow-md"
              onClick={() => router.push(`/menu/${cat.id}`)}
            >
              <CardContent className="flex items-center justify-between p-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">{cat.name}</span>
                    {cat.nameHe && (
                      <span className="text-sm text-muted-foreground dir-rtl">{cat.nameHe}</span>
                    )}
                  </div>
                  <Badge variant={cat.active ? 'success' : 'secondary'} className="mt-1">
                    {cat.active ? 'Active' : 'Hidden'}
                  </Badge>
                </div>
                <div className="flex shrink-0 items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => { e.stopPropagation(); openEdit(cat) }}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={(e) => { e.stopPropagation(); handleDelete(cat.id) }}
                    disabled={deletingId === cat.id}
                  >
                    {deletingId === cat.id ? (
                      <Spinner className="h-4 w-4" />
                    ) : (
                      <Trash2 className="h-4 w-4 text-destructive" />
                    )}
                  </Button>
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                </div>
              </CardContent>
            </Card>
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
    </div>
  )
}
