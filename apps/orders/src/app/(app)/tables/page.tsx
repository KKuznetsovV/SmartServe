'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useTranslations } from 'next-intl'
import { ROLE_RANK, type UserRole } from '@smartserve/types'
import { formatPrice } from '@smartserve/ui'
import { useTables, useCreateTable, useUpdateTable, useDeleteTable } from '@/hooks/use-tables'
import { useCreateOrder } from '@/hooks/use-orders'
import { useLocationWs } from '@/hooks/use-ws'
import { useAuthStore } from '@/lib/auth-store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import type { Table, TableFloorState } from '@smartserve/types'

const tableSchema = z.object({
  name: z.string().min(1, 'Required'),
  capacity: z.coerce.number().int().min(1),
  section: z.string().optional(),
})
type TableForm = z.infer<typeof tableSchema>

const STATE_CLASS: Record<TableFloorState, string> = {
  free: 'border-zinc-300 bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-900',
  seated: 'border-sky-400 bg-sky-50 dark:border-sky-700 dark:bg-sky-950/50',
  ordered: 'border-amber-400 bg-amber-50 dark:border-amber-700 dark:bg-amber-950/50',
  food_ready: 'border-emerald-400 bg-emerald-50 dark:border-emerald-700 dark:bg-emerald-950/50',
  waiting_to_pay: 'border-violet-400 bg-violet-50 dark:border-violet-700 dark:bg-violet-950/50',
}

const STATE_KEY: Record<TableFloorState, 'stateFree' | 'stateSeated' | 'stateOrdered' | 'stateFoodReady' | 'stateWaitingToPay'> = {
  free: 'stateFree',
  seated: 'stateSeated',
  ordered: 'stateOrdered',
  food_ready: 'stateFoodReady',
  waiting_to_pay: 'stateWaitingToPay',
}

export default function TablesPage() {
  const t = useTranslations('tables')
  const tCommon = useTranslations('common')
  const router = useRouter()
  const locationId = useAuthStore((s) => s.activeLocationId)
  const role = useAuthStore((s) => s.user?.role) as UserRole | undefined
  const canEditLayout = !!role && ROLE_RANK[role] >= ROLE_RANK.manager
  const { data: tables, isLoading } = useTables(locationId, true)
  const createTable = useCreateTable()
  const updateTable = useUpdateTable()
  const deleteTable = useDeleteTable()
  const createOrder = useCreateOrder()
  useLocationWs(locationId)

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Table | null>(null)
  const [layoutMode, setLayoutMode] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TableForm>({ resolver: zodResolver(tableSchema) })

  function openCreate() {
    setEditing(null)
    reset({ name: '', capacity: 4, section: '' })
    setDialogOpen(true)
  }

  function openEdit(tbl: Table) {
    setEditing(tbl)
    reset({ name: tbl.name, capacity: tbl.capacity, section: tbl.section ?? '' })
    setDialogOpen(true)
  }

  async function onSubmit(values: TableForm) {
    const payload = { ...values, section: values.section || undefined }
    if (editing) {
      await updateTable.mutateAsync({ id: editing.id, data: payload })
    } else {
      if (!locationId) return
      await createTable.mutateAsync({ locationId, active: true, posX: 0, posY: 0, ...payload })
    }
    setDialogOpen(false)
  }

  async function handleDelete(tbl: Table) {
    if (!confirm(t('deleteConfirm', { name: tbl.name }))) return
    await deleteTable.mutateAsync({ id: tbl.id, locationId: tbl.locationId })
  }

  async function openTable(tbl: Table) {
    if (layoutMode) return
    if (tbl.openOrder?.id) {
      router.push(`/orders/${tbl.openOrder.id}`)
      return
    }
    if (!locationId) return
    const order = await createOrder.mutateAsync({
      locationId,
      tableId: tbl.id,
      channel: 'dine_in',
      guestCount: 1,
    })
    router.push(`/orders/${order.id}`)
  }

  const placed = (tables ?? []).filter((tbl) => tbl.posX || tbl.posY)
  const usePositions = placed.length > 0

  return (
    <main className="space-y-6 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t('title')}</h1>
        <div className="flex gap-2">
          {canEditLayout && (
            <Button
              variant="outline"
              className="min-h-12"
              onClick={() => setLayoutMode((v) => !v)}
            >
              {layoutMode ? t('doneLayout') : t('editLayout')}
            </Button>
          )}
          {canEditLayout && layoutMode && (
            <Button className="min-h-12" onClick={openCreate}>
              + {t('addTable')}
            </Button>
          )}
        </div>
      </div>

      {isLoading && <Spinner />}

      {!isLoading && tables?.length === 0 && (
        <p className="text-muted-foreground">{t('noTables')}</p>
      )}

      <div
        className={
          usePositions
            ? 'relative min-h-[28rem] rounded-lg border bg-muted/30'
            : 'grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6'
        }
      >
        {(tables ?? []).map((tbl) => {
          const state = (tbl.floorState ?? 'free') as TableFloorState
          const style = usePositions
            ? {
                position: 'absolute' as const,
                insetInlineStart: `${Math.min(90, Math.max(0, tbl.posX))}%`,
                top: `${Math.min(90, Math.max(0, tbl.posY))}%`,
                width: '7rem',
              }
            : undefined
          return (
            <Card
              key={tbl.id}
              data-testid="table-card"
              data-floor-state={state}
              role="button"
              tabIndex={0}
              onClick={() => void openTable(tbl)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') void openTable(tbl)
              }}
              style={style}
              className={`min-h-16 cursor-pointer border-2 ${STATE_CLASS[state]} ${!tbl.active ? 'opacity-50' : ''}`}
            >
              <CardHeader className="p-3 pb-0">
                <CardTitle className="text-base">{tbl.name}</CardTitle>
              </CardHeader>
              <CardContent className="p-3 pt-1 text-xs">
                <p className="font-medium">{t(STATE_KEY[state])}</p>
                {tbl.openOrder && (
                  <>
                    <p>
                      {t('seatedSince', {
                        time: new Date(tbl.openOrder.seatedSince).toLocaleTimeString('he-IL', {
                          hour: '2-digit',
                          minute: '2-digit',
                        }),
                      })}
                    </p>
                    {tbl.openOrder.guestCount != null && <p>{t('guests', { count: tbl.openOrder.guestCount })}</p>}
                    <p className="font-semibold">{formatPrice(tbl.openOrder.total)}</p>
                  </>
                )}
                {layoutMode && canEditLayout && (
                  <div className="mt-2 flex gap-1" onClick={(e) => e.stopPropagation()}>
                    <Button variant="outline" className="min-h-12 min-w-12" onClick={() => openEdit(tbl)}>
                      {tCommon('edit')}
                    </Button>
                    <Button
                      variant="outline"
                      className="min-h-12 text-destructive hover:text-destructive"
                      onClick={() => handleDelete(tbl)}
                    >
                      {t('del')}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>{editing ? t('editTable') : t('addTableTitle')}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1">
              <Label>{t('nameLabel')}</Label>
              <Input {...register('name')} placeholder="e.g. T1" />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-1">
              <Label>{t('capacityLabel')}</Label>
              <Input type="number" min={1} {...register('capacity')} />
              {errors.capacity && <p className="text-xs text-destructive">{errors.capacity.message}</p>}
            </div>
            <div className="space-y-1">
              <Label>{t('sectionLabel')}</Label>
              <Input {...register('section')} placeholder="e.g. Main, Bar, Terrace" />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" className="min-h-12" onClick={() => setDialogOpen(false)}>
                {tCommon('cancel')}
              </Button>
              <Button className="min-h-12" type="submit" disabled={createTable.isPending || updateTable.isPending}>
                {editing ? tCommon('save') : tCommon('create')}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </main>
  )
}
