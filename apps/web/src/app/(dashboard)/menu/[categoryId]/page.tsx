'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  ArrowLeft,
  Plus,
  Pencil,
  Trash2,
  Power,
  PowerOff,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogClose } from '@/components/ui/dialog'
import { Spinner } from '@/components/ui/spinner'
import {
  useMenuItems,
  useCreateMenuItem,
  useUpdateMenuItem,
  useDeleteMenuItem,
  useToggleItemStock,
  useCreateModifierGroup,
  useDeleteModifierGroup,
} from '@/hooks/use-menu'
import { formatPrice } from '@/lib/utils'
import type { MenuItem, ModifierGroup } from '@smartserve/types'

// ─── Schemas ──────────────────────────────────────────────────────────────────

const itemSchema = z.object({
  name: z.string().min(1, 'Name required'),
  nameHe: z.string().optional(),
  description: z.string().optional(),
  price: z.coerce.number().positive('Price must be positive'),
  taxRate: z.coerce.number().min(0).max(1).default(0.17),
  preparationTimeMin: z.coerce.number().int().min(0).default(10),
})
type ItemFormData = z.infer<typeof itemSchema>

const modifierGroupSchema = z.object({
  name: z.string().min(1, 'Name required'),
  nameHe: z.string().optional(),
  required: z.boolean().default(false),
  minSelect: z.coerce.number().int().min(0).default(0),
  maxSelect: z.coerce.number().int().min(1).default(1),
  modifiers: z
    .array(
      z.object({
        name: z.string().min(1),
        nameHe: z.string().optional(),
        priceDelta: z.coerce.number().default(0),
      }),
    )
    .min(1, 'Add at least one option'),
})
type ModifierGroupFormData = z.infer<typeof modifierGroupSchema>

// ─── Modifier Group Dialog ────────────────────────────────────────────────────

function ModifierGroupDialog({
  open,
  onOpenChange,
  menuItemId,
}: {
  open: boolean
  onOpenChange: (v: boolean) => void
  menuItemId: string
}) {
  const createMG = useCreateModifierGroup()
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<ModifierGroupFormData>({
    resolver: zodResolver(modifierGroupSchema),
    defaultValues: { required: false, modifiers: [{ name: '', priceDelta: 0 }] },
  })
  const { fields, append, remove } = useFieldArray({ control, name: 'modifiers' })

  const onSubmit = async (data: ModifierGroupFormData) => {
    await createMG.mutateAsync({
      itemId: menuItemId,
      name: data.name,
      nameHe: data.nameHe || undefined,
      required: data.required,
      minSelect: data.minSelect,
      maxSelect: data.maxSelect,
      modifiers: data.modifiers.map((m) => ({
        id: crypto.randomUUID(),
        groupId: crypto.randomUUID(),
        name: m.name,
        nameHe: m.nameHe || undefined,
        priceDelta: m.priceDelta,
        active: true,
      })) as ModifierGroup['modifiers'],
    })
    reset()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Add Modifier Group</DialogTitle>
          <DialogClose onClose={() => onOpenChange(false)} />
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Group Name</Label>
              <Input {...register('name')} placeholder="e.g. Size" />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-1">
              <Label>שם (עברית)</Label>
              <Input {...register('nameHe')} placeholder="גודל" dir="rtl" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label>Min Selections</Label>
              <Input type="number" {...register('minSelect')} defaultValue={0} />
            </div>
            <div className="space-y-1">
              <Label>Max Selections</Label>
              <Input type="number" {...register('maxSelect')} defaultValue={1} />
            </div>
          </div>

          <div>
            <Label>Options</Label>
            {errors.modifiers?.root && (
              <p className="text-xs text-destructive">{errors.modifiers.root.message}</p>
            )}
            <div className="mt-2 space-y-2">
              {fields.map((field, idx) => (
                <div key={field.id} className="flex gap-2">
                  <Input
                    {...register(`modifiers.${idx}.name`)}
                    placeholder="Option name"
                    className="flex-1"
                  />
                  <Input
                    {...register(`modifiers.${idx}.priceDelta`)}
                    type="number"
                    step="0.01"
                    placeholder="±price"
                    className="w-24"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => remove(idx)}
                    disabled={fields.length === 1}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => append({ name: '', priceDelta: 0 })}
              >
                <Plus className="mr-1 h-3 w-3" />
                Add Option
              </Button>
            </div>
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createMG.isPending}>
              {createMG.isPending && <Spinner className="mr-2 h-4 w-4" />}
              Create Group
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ─── Item Row / Card ──────────────────────────────────────────────────────────

function ItemCard({
  item,
  categoryId,
  onEdit,
}: {
  item: MenuItem
  categoryId: string
  onEdit: (item: MenuItem) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [mgDialogOpen, setMgDialogOpen] = useState(false)
  const deleteItem = useDeleteMenuItem()
  const toggleStock = useToggleItemStock()
  const deleteMG = useDeleteModifierGroup()

  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={() => setExpanded((v) => !v)}
      onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setExpanded((v) => !v)}
      className="cursor-pointer select-none transition-shadow hover:shadow-md"
    >
      <CardContent className="space-y-2 p-4">
        {/* Compact rectangle: name + price + stock badge, always visible */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <span className="block truncate font-medium">{item.name}</span>
            {item.nameHe && (
              <span className="block truncate text-xs text-muted-foreground" dir="rtl">
                {item.nameHe}
              </span>
            )}
          </div>
          {expanded ? (
            <ChevronUp className="h-4 w-4 shrink-0 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
          )}
        </div>
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold">{formatPrice(item.price)}</span>
          <Badge variant={item.inStock ? 'success' : 'warning'}>
            {item.inStock ? 'In Stock' : 'Out of Stock'}
          </Badge>
        </div>

        {/* Expanded: description + edit options + modifier groups */}
        {expanded && (
          <div className="space-y-3 border-t pt-3" onClick={(e) => e.stopPropagation()}>
            {item.description && <p className="text-xs text-muted-foreground">{item.description}</p>}

            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => toggleStock.mutate({ id: item.id, inStock: !item.inStock, categoryId })}
                title={item.inStock ? 'Mark out of stock' : 'Mark in stock'}
              >
                {item.inStock ? (
                  <Power className="h-4 w-4 text-emerald-600" />
                ) : (
                  <PowerOff className="h-4 w-4 text-amber-500" />
                )}
              </Button>
              <Button variant="ghost" size="icon" onClick={() => onEdit(item)}>
                <Pencil className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => deleteItem.mutate({ id: item.id, categoryId })}
                disabled={deleteItem.isPending}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>

            {item.modifierGroups && item.modifierGroups.length > 0 && (
              <div className="space-y-3">
                {item.modifierGroups.map((mg: ModifierGroup) => (
                  <div key={mg.id} className="rounded-md bg-muted/50 p-3">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-sm font-medium">{mg.name}</span>
                      <Button variant="ghost" size="sm" onClick={() => deleteMG.mutate({ id: mg.id, itemId: item.id })}>
                        <Trash2 className="h-3 w-3 text-destructive" />
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {mg.modifiers?.map((mod) => (
                        <Badge key={mod.id} variant="outline" className="text-xs">
                          {mod.name}
                          {mod.priceDelta !== 0 && (
                            <span className="ml-1 text-muted-foreground">
                              {mod.priceDelta > 0 ? '+' : ''}
                              {formatPrice(mod.priceDelta)}
                            </span>
                          )}
                        </Badge>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <Button
              variant="ghost"
              size="sm"
              className="text-xs text-muted-foreground"
              onClick={() => setMgDialogOpen(true)}
            >
              <Plus className="mr-1 h-3 w-3" />
              Add Modifier Group
            </Button>
          </div>
        )}
      </CardContent>
      <ModifierGroupDialog
        open={mgDialogOpen}
        onOpenChange={setMgDialogOpen}
        menuItemId={item.id}
      />
    </Card>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function CategoryItemsPage() {
  const params = useParams()
  const router = useRouter()
  const categoryId = params.categoryId as string

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<MenuItem | null>(null)

  const { data: items = [], isLoading } = useMenuItems(categoryId)
  const createItem = useCreateMenuItem()
  const updateItem = useUpdateMenuItem()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ItemFormData>({ resolver: zodResolver(itemSchema) })

  const openCreate = () => {
    setEditing(null)
    reset({ name: '', price: 0, taxRate: 0.17, preparationTimeMin: 10 })
    setDialogOpen(true)
  }

  const openEdit = (item: MenuItem) => {
    setEditing(item)
    reset({
      name: item.name,
      nameHe: item.nameHe ?? '',
      description: item.description ?? '',
      price: item.price,
      taxRate: item.taxRate,
      preparationTimeMin: item.preparationTimeMin,
    })
    setDialogOpen(true)
  }

  const onSubmit = async (data: ItemFormData) => {
    if (editing) {
      await updateItem.mutateAsync({ id: editing.id, data })
    } else {
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
    setDialogOpen(false)
    reset()
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.push('/menu')}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Menu Items</h1>
          <p className="text-sm text-muted-foreground">
            {items.length} item{items.length !== 1 ? 's' : ''}
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="mr-1 h-4 w-4" />
          Add Item
        </Button>
      </div>

      {/* Items */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
          <p className="mb-4 text-muted-foreground">No items in this category yet</p>
          <Button variant="outline" onClick={openCreate}>
            <Plus className="mr-1 h-4 w-4" />
            Add first item
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 items-start gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {items.map((item) => (
            <ItemCard key={item.id} item={item} categoryId={categoryId} onEdit={openEdit} />
          ))}
        </div>
      )}

      {/* Item Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit Item' : 'New Item'}</DialogTitle>
            <DialogClose onClose={() => setDialogOpen(false)} />
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
              <Textarea
                {...register('description')}
                placeholder="Optional description..."
                rows={2}
              />
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
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createItem.isPending || updateItem.isPending}
              >
                {(createItem.isPending || updateItem.isPending) && (
                  <Spinner className="mr-2 h-4 w-4" />
                )}
                {editing ? 'Save Changes' : 'Create Item'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
