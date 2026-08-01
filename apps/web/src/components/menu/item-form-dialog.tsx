'use client'

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose } from '@/components/ui/dialog'
import { Spinner } from '@/components/ui/spinner'
import { useCreateMenuItem, useUpdateMenuItem } from '@/hooks/use-menu'
import type { MenuItem } from '@smartserve/types'

const itemSchema = z.object({
  name: z.string().min(1, 'Name required'),
  nameHe: z.string().optional(),
  description: z.string().optional(),
  price: z.coerce.number().positive('Price must be positive'),
  taxRate: z.coerce.number().min(0).max(1).default(0.17),
  preparationTimeMin: z.coerce.number().int().min(0).default(10),
})
type ItemFormData = z.infer<typeof itemSchema>

export function ItemFormDialog({
  open,
  onOpenChange,
  categoryId,
  editing,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  categoryId: string | null
  editing: MenuItem | null
}) {
  const createItem = useCreateMenuItem()
  const updateItem = useUpdateMenuItem()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ItemFormData>({ resolver: zodResolver(itemSchema) })

  useEffect(() => {
    if (!open) return
    if (editing) {
      reset({
        name: editing.name,
        nameHe: editing.nameHe ?? '',
        description: editing.description ?? '',
        price: editing.price,
        taxRate: editing.taxRate,
        preparationTimeMin: editing.preparationTimeMin,
      })
    } else {
      reset({ name: '', price: 0, taxRate: 0.17, preparationTimeMin: 10 })
    }
  }, [open, editing, reset])

  const onSubmit = async (data: ItemFormData) => {
    if (editing) {
      await updateItem.mutateAsync({ id: editing.id, data })
    } else {
      if (!categoryId) return
      await createItem.mutateAsync({
        categoryId,
        name: data.name,
        nameHe: data.nameHe || undefined,
        description: data.description || undefined,
        price: data.price,
        taxRate: data.taxRate,
        preparationTimeMin: data.preparationTimeMin,
        active: true,
        inStock: true,
        imageUrl: undefined,
      })
    }
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{editing ? 'Edit Item' : 'New Item'}</DialogTitle>
          <DialogClose onClose={() => onOpenChange(false)} />
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Name (English)</Label>
              <Input {...register('name')} placeholder="e.g. Margherita Pizza" />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-1">
              <Label>שם (עברית)</Label>
              <Input {...register('nameHe')} placeholder="פיצה מרגריטה" dir="rtl" />
            </div>
          </div>
          <div className="space-y-1">
            <Label>Description</Label>
            <Textarea {...register('description')} placeholder="Optional description..." rows={2} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1">
              <Label>Price (₪)</Label>
              <Input type="number" step="0.01" {...register('price')} />
              {errors.price && <p className="text-xs text-destructive">{errors.price.message}</p>}
            </div>
            <div className="space-y-1">
              <Label>Tax Rate</Label>
              <Input type="number" step="0.01" {...register('taxRate')} />
            </div>
            <div className="space-y-1">
              <Label>Prep Time (min)</Label>
              <Input type="number" {...register('preparationTimeMin')} />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createItem.isPending || updateItem.isPending}>
              {(createItem.isPending || updateItem.isPending) && <Spinner className="mr-2 h-4 w-4" />}
              {editing ? 'Save Changes' : 'Create Item'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
