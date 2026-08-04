'use client'

import { useState } from 'react'
import { useCategories, useMenuItems } from '@/hooks/use-menu'
import { useAddOrderItem } from '@/hooks/use-orders'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { formatPrice } from '@/lib/utils'
import type { MenuItem, Modifier, ModifierGroup } from '@smartserve/types'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  orderId: string
  locationId: string
}

export function AddItemDialog({ open, onOpenChange, orderId, locationId }: Props) {
  const { data: categories } = useCategories(locationId)
  const [categoryId, setCategoryId] = useState<string | null>(null)
  const { data: items, isLoading: itemsLoading } = useMenuItems(categoryId, !!categoryId)
  const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null)
  const [qty, setQty] = useState(1)
  const [notes, setNotes] = useState('')
  // groupId -> selected modifier ids
  const [selectedModifiers, setSelectedModifiers] = useState<Record<string, string[]>>({})
  const addItem = useAddOrderItem()

  function reset() {
    setCategoryId(null)
    setSelectedItem(null)
    setQty(1)
    setNotes('')
    setSelectedModifiers({})
  }

  function handleOpenChange(isOpen: boolean) {
    if (!isOpen) reset()
    onOpenChange(isOpen)
  }

  function selectItem(item: MenuItem) {
    setSelectedItem(item)
    setQty(1)
    setNotes('')
    setSelectedModifiers({})
  }

  function toggleModifier(group: ModifierGroup, modifier: Modifier) {
    setSelectedModifiers((prev) => {
      const current = prev[group.id] ?? []
      const isSelected = current.includes(modifier.id)
      if (isSelected) return { ...prev, [group.id]: current.filter((id) => id !== modifier.id) }
      // single-select groups replace the current pick, multi-select groups append up to maxSelect
      if (group.maxSelect <= 1) return { ...prev, [group.id]: [modifier.id] }
      if (current.length >= group.maxSelect) return prev
      return { ...prev, [group.id]: [...current, modifier.id] }
    })
  }

  const modifierGroups = selectedItem?.modifierGroups ?? []
  const canSubmit = modifierGroups.every((g) => {
    const count = (selectedModifiers[g.id] ?? []).length
    return !g.required || count >= Math.max(1, g.minSelect)
  })

  async function handleAdd() {
    if (!selectedItem || !canSubmit) return
    const modifiers = modifierGroups.flatMap((g) =>
      (selectedModifiers[g.id] ?? []).flatMap((modId) => {
        const mod = g.modifiers.find((m) => m.id === modId)
        return mod ? [{ modifierId: mod.id, name: mod.name, priceDelta: mod.priceDelta }] : []
      }),
    )
    const unitPrice = selectedItem.price + modifiers.reduce((sum, m) => sum + m.priceDelta, 0)
    await addItem.mutateAsync({
      orderId,
      locationId,
      item: {
        menuItemId: selectedItem.id,
        menuItemName: selectedItem.name,
        qty,
        unitPrice,
        modifiers,
        notes: notes || undefined,
      },
    })
    reset()
    onOpenChange(false)
  }

  const availableItems = (items ?? []).filter((i) => i.active && i.inStock)

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Add Item</DialogTitle>
        </DialogHeader>

        {!selectedItem ? (
          <div className="grid grid-cols-[160px_1fr] gap-4">
            <div className="max-h-[50vh] space-y-1 overflow-y-auto border-r pr-2">
              {categories?.map((cat) => (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => setCategoryId(cat.id)}
                  className={`w-full rounded-md px-2 py-1.5 text-left text-sm transition-colors ${
                    categoryId === cat.id
                      ? 'bg-primary text-primary-foreground'
                      : 'hover:bg-muted'
                  }`}
                >
                  {cat.name}
                </button>
              ))}
            </div>

            <div className="max-h-[50vh] space-y-1 overflow-y-auto pr-1">
              {!categoryId && <p className="p-2 text-sm text-muted-foreground">Select a category</p>}
              {itemsLoading && <Spinner />}
              {availableItems.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => selectItem(item)}
                  className="flex w-full items-center justify-between rounded-md border p-2 text-left text-sm hover:bg-muted"
                >
                  <span>{item.name}</span>
                  <span className="font-medium">{formatPrice(item.price)}</span>
                </button>
              ))}
              {categoryId && !itemsLoading && availableItems.length === 0 && (
                <p className="p-2 text-sm text-muted-foreground">No available items</p>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <button
              type="button"
              onClick={() => setSelectedItem(null)}
              className="text-sm text-muted-foreground hover:underline"
            >
              ← Back to menu
            </button>

            <div>
              <p className="font-medium">{selectedItem.name}</p>
              <p className="text-sm text-muted-foreground">{formatPrice(selectedItem.price)}</p>
            </div>

            {modifierGroups.map((group) => (
              <div key={group.id} className="space-y-1">
                <Label>
                  {group.name}
                  {group.required && <span className="text-destructive"> *</span>}
                  <span className="ml-1 text-xs text-muted-foreground">
                    {group.maxSelect > 1 ? `up to ${group.maxSelect}` : 'choose one'}
                  </span>
                </Label>
                <div className="flex flex-wrap gap-2">
                  {group.modifiers
                    .filter((m) => m.active)
                    .map((mod) => {
                      const selected = (selectedModifiers[group.id] ?? []).includes(mod.id)
                      return (
                        <button
                          key={mod.id}
                          type="button"
                          onClick={() => toggleModifier(group, mod)}
                          className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                            selected
                              ? 'border-primary bg-primary/10 font-medium text-primary'
                              : 'border-border hover:bg-muted'
                          }`}
                        >
                          {mod.name}
                          {mod.priceDelta !== 0 &&
                            ` (${mod.priceDelta > 0 ? '+' : ''}${formatPrice(mod.priceDelta)})`}
                        </button>
                      )
                    })}
                </div>
              </div>
            ))}

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Quantity</Label>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => setQty((q) => Math.max(1, q - 1))}
                  >
                    −
                  </Button>
                  <span className="w-8 text-center">{qty}</span>
                  <Button type="button" variant="outline" size="icon" onClick={() => setQty((q) => q + 1)}>
                    +
                  </Button>
                </div>
              </div>
              <div className="space-y-1">
                <Label>Notes (optional)</Label>
                <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="e.g. no ice" />
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setSelectedItem(null)}>
                Cancel
              </Button>
              <Button type="button" onClick={handleAdd} disabled={!canSubmit || addItem.isPending}>
                {addItem.isPending && <Spinner className="mr-2 h-4 w-4" />}
                Add to Order
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
