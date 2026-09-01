'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { formatPrice } from '@/lib/utils'
import type { MenuItem, Modifier, ModifierGroup } from '@smartserve/types'

export interface ItemConfigResult {
  qty: number
  notes?: string
  modifiers: { modifierId: string; name: string; priceDelta: number }[]
  unitPrice: number
  fireCourse?: number
}

export interface ItemConfigInitial {
  qty: number
  notes?: string
  modifierIds: string[]
  fireCourse?: number
}

interface Props {
  /** Controls dialog visibility independently of `item`, since edit mode may still be loading the item. */
  open: boolean
  item: MenuItem | null
  onOpenChange: (open: boolean) => void
  onConfirm: (result: ItemConfigResult) => void
  pending?: boolean
  initial?: ItemConfigInitial
  title?: string
  confirmLabel?: string
}

/** Quantity/notes/modifier picker shown before adding an item that has modifier groups, or when editing one already on the order. */
export function ItemConfigDialog({
  open,
  item,
  onOpenChange,
  onConfirm,
  pending,
  initial,
  title,
  confirmLabel,
}: Props) {
  const t = useTranslations('itemConfigDialog')
  const tCommon = useTranslations('common')
  const [qty, setQty] = useState(1)
  const [notes, setNotes] = useState('')
  const [selectedModifiers, setSelectedModifiers] = useState<Record<string, string[]>>({})
  const [fireCourse, setFireCourse] = useState(1)

  useEffect(() => {
    if (!item) return
    if (initial) {
      setQty(initial.qty)
      setNotes(initial.notes ?? '')
      setFireCourse(initial.fireCourse ?? item.defaultFireCourse)
      const byGroup: Record<string, string[]> = {}
      for (const group of item.modifierGroups) {
        const ids = group.modifiers.filter((m) => initial.modifierIds.includes(m.id)).map((m) => m.id)
        if (ids.length > 0) byGroup[group.id] = ids
      }
      setSelectedModifiers(byGroup)
    } else {
      setQty(1)
      setNotes('')
      setFireCourse(item.defaultFireCourse)
      setSelectedModifiers({})
    }
  }, [item, initial])

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

  const modifierGroups = item?.modifierGroups ?? []
  const canSubmit = modifierGroups.every((g) => {
    const count = (selectedModifiers[g.id] ?? []).length
    return !g.required || count >= Math.max(1, g.minSelect)
  })

  function handleConfirm() {
    if (!item || !canSubmit) return
    const modifiers = modifierGroups.flatMap((g) =>
      (selectedModifiers[g.id] ?? []).flatMap((modId) => {
        const mod = g.modifiers.find((m) => m.id === modId)
        return mod ? [{ modifierId: mod.id, name: mod.name, priceDelta: mod.priceDelta }] : []
      }),
    )
    const unitPrice = item.price + modifiers.reduce((sum, m) => sum + m.priceDelta, 0)
    onConfirm({ qty, notes: notes || undefined, modifiers, unitPrice, fireCourse })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{title ?? item?.name}</DialogTitle>
        </DialogHeader>

        {!item && (
          <div className="flex justify-center py-6">
            <Spinner />
          </div>
        )}

        {item && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">{formatPrice(item.price)}</p>

            {modifierGroups.map((group) => (
              <div key={group.id} className="space-y-1">
                <Label>
                  {group.name}
                  {group.required && <span className="text-destructive"> *</span>}
                  <span className="ms-1 text-xs text-muted-foreground">
                    {group.maxSelect > 1 ? t('upTo', { max: group.maxSelect }) : t('chooseOne')}
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
                <Label>{t('quantity')}</Label>
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
                <Label>{t('notesOptional')}</Label>
                <Input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder={t('notesPlaceholder')} />
              </div>
            </div>

            <div className="space-y-1">
              <Label>{t('fireCourse')}</Label>
              <Select value={fireCourse} onChange={(e) => setFireCourse(Number(e.target.value))}>
                {[1, 2, 3, 4, 5].map((course) => (
                  <option key={course} value={course}>
                    {course === 1 ? t('firesImmediately') : course}
                  </option>
                ))}
              </Select>
            </div>

            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                {tCommon('cancel')}
              </Button>
              <Button type="button" onClick={handleConfirm} disabled={!canSubmit || pending}>
                {pending && <Spinner className="me-2 h-4 w-4" />}
                {confirmLabel ?? t('addToOrder')}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
