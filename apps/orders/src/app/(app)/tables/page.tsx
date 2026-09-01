'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useTranslations } from 'next-intl'
import { useTables, useCreateTable, useUpdateTable, useDeleteTable } from '@/hooks/use-tables'
import { useAuthStore } from '@/lib/auth-store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import type { Table } from '@smartserve/types'

const tableSchema = z.object({
  name: z.string().min(1, 'Required'),
  capacity: z.coerce.number().int().min(1),
  section: z.string().optional(),
})
type TableForm = z.infer<typeof tableSchema>

const SECTION_COLORS: Record<string, string> = {
  Main: 'bg-blue-50 border-blue-200 dark:bg-blue-950/40 dark:border-blue-900',
  Bar: 'bg-amber-50 border-amber-200 dark:bg-amber-950/40 dark:border-amber-900',
  Terrace: 'bg-green-50 border-green-200 dark:bg-green-950/40 dark:border-green-900',
  Private: 'bg-purple-50 border-purple-200 dark:bg-purple-950/40 dark:border-purple-900',
}

function sectionColor(section?: string) {
  return (section && SECTION_COLORS[section]) ?? 'bg-gray-50 border-gray-200 dark:bg-gray-900/40 dark:border-gray-800'
}

export default function TablesPage() {
  const t = useTranslations('tables')
  const tCommon = useTranslations('common')
  const locationId = useAuthStore((s) => s.activeLocationId)
  const { data: tables, isLoading } = useTables(locationId)
  const createTable = useCreateTable()
  const updateTable = useUpdateTable()
  const deleteTable = useDeleteTable()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Table | null>(null)

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

  function openEdit(t: Table) {
    setEditing(t)
    reset({ name: t.name, capacity: t.capacity, section: t.section ?? '' })
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

  const grouped = (tables ?? []).reduce<Record<string, Table[]>>((acc, t) => {
    const key = t.section ?? 'Main'
    ;(acc[key] ??= []).push(t)
    return acc
  }, {})

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('title')}</h1>
        <Button onClick={openCreate}>+ {t('addTable')}</Button>
      </div>

      {isLoading && <Spinner />}

      {!isLoading && tables?.length === 0 && (
        <p className="text-muted-foreground">{t('noTables')}</p>
      )}

      {Object.entries(grouped).map(([section, sectionTables]) => (
        <div key={section}>
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            {section}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {sectionTables.map((tbl) => (
              <Card
                key={tbl.id}
                className={`border-2 cursor-default ${sectionColor(tbl.section)} ${!tbl.active ? 'opacity-50' : ''}`}
              >
                <CardHeader className="p-3 pb-0">
                  <CardTitle className="text-base">{tbl.name}</CardTitle>
                </CardHeader>
                <CardContent className="p-3 pt-1">
                  <p className="text-xs text-muted-foreground">{t('seats', { count: tbl.capacity })}</p>
                  <div className="flex gap-1 mt-2">
                    <Button variant="outline" size="sm" className="h-6 text-xs px-2" onClick={() => openEdit(tbl)}>
                      {tCommon('edit')}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-6 text-xs px-2 text-destructive hover:text-destructive"
                      onClick={() => handleDelete(tbl)}
                    >
                      {t('del')}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      ))}

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
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                {tCommon('cancel')}
              </Button>
              <Button type="submit" disabled={createTable.isPending || updateTable.isPending}>
                {editing ? tCommon('save') : tCommon('create')}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
