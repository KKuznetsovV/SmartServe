'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
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
  Main: 'bg-blue-50 border-blue-200',
  Bar: 'bg-amber-50 border-amber-200',
  Terrace: 'bg-green-50 border-green-200',
  Private: 'bg-purple-50 border-purple-200',
}

function sectionColor(section?: string) {
  return (section && SECTION_COLORS[section]) ?? 'bg-gray-50 border-gray-200'
}

export default function TablesPage() {
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

  async function handleDelete(t: Table) {
    if (!confirm(`Delete table "${t.name}"?`)) return
    await deleteTable.mutateAsync({ id: t.id, locationId: t.locationId })
  }

  const grouped = (tables ?? []).reduce<Record<string, Table[]>>((acc, t) => {
    const key = t.section ?? 'Main'
    ;(acc[key] ??= []).push(t)
    return acc
  }, {})

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Floor Plan</h1>
        <Button onClick={openCreate}>+ Add Table</Button>
      </div>

      {isLoading && <Spinner />}

      {!isLoading && tables?.length === 0 && (
        <p className="text-muted-foreground">No tables yet. Add your first table.</p>
      )}

      {Object.entries(grouped).map(([section, sectionTables]) => (
        <div key={section}>
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            {section}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {sectionTables.map((t) => (
              <Card
                key={t.id}
                className={`border-2 cursor-default ${sectionColor(t.section)} ${!t.active ? 'opacity-50' : ''}`}
              >
                <CardHeader className="p-3 pb-0">
                  <CardTitle className="text-base">{t.name}</CardTitle>
                </CardHeader>
                <CardContent className="p-3 pt-1">
                  <p className="text-xs text-muted-foreground">{t.capacity} seats</p>
                  <div className="flex gap-1 mt-2">
                    <Button variant="outline" size="sm" className="h-6 text-xs px-2" onClick={() => openEdit(t)}>
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-6 text-xs px-2 text-destructive hover:text-destructive"
                      onClick={() => handleDelete(t)}
                    >
                      Del
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
            <DialogTitle>{editing ? 'Edit Table' : 'Add Table'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1">
              <Label>Name</Label>
              <Input {...register('name')} placeholder="e.g. T1" />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-1">
              <Label>Capacity (seats)</Label>
              <Input type="number" min={1} {...register('capacity')} />
              {errors.capacity && <p className="text-xs text-destructive">{errors.capacity.message}</p>}
            </div>
            <div className="space-y-1">
              <Label>Section (optional)</Label>
              <Input {...register('section')} placeholder="e.g. Main, Bar, Terrace" />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createTable.isPending || updateTable.isPending}>
                {editing ? 'Save' : 'Create'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
