'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  usePrinters,
  usePrinterRoutes,
  useCreatePrinter,
  useUpdatePrinter,
  useDeletePrinter,
  useSetPrinterRoute,
} from '@/hooks/use-printers'
import { useCategories } from '@/hooks/use-menu'
import { useAuthStore } from '@/lib/auth-store'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import type { Printer, PrinterType } from '@smartserve/types'

const TYPE_LABELS: Record<PrinterType, string> = {
  receipt: 'Receipt',
  kitchen: 'Kitchen',
  label: 'Label',
}

const TYPE_VARIANT: Record<PrinterType, 'default' | 'secondary' | 'outline'> = {
  receipt: 'default',
  kitchen: 'secondary',
  label: 'outline',
}

const printerSchema = z.object({
  name: z.string().min(1, 'Required'),
  type: z.enum(['receipt', 'kitchen', 'label']),
  ip: z.string().optional().or(z.literal('')),
  port: z.coerce.number().int().min(1).max(65535),
})
type PrinterForm = z.infer<typeof printerSchema>

export default function PrintersPage() {
  const locationId = useAuthStore((s) => s.activeLocationId)
  const { data: printers, isLoading } = usePrinters(locationId)
  const { data: routes } = usePrinterRoutes(locationId)
  const { data: categories } = useCategories(locationId)
  const createPrinter = useCreatePrinter()
  const updatePrinter = useUpdatePrinter()
  const deletePrinter = useDeletePrinter()
  const setRoute = useSetPrinterRoute()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<Printer | null>(null)

  const { register, handleSubmit, reset, formState: { errors } } = useForm<PrinterForm>({
    resolver: zodResolver(printerSchema),
  })

  function openCreate() {
    setEditing(null)
    reset({ name: '', type: 'receipt', ip: '', port: 9100 })
    setDialogOpen(true)
  }

  function openEdit(p: Printer) {
    setEditing(p)
    reset({ name: p.name, type: p.type as PrinterType, ip: p.ip ?? '', port: p.port })
    setDialogOpen(true)
  }

  async function onSubmit(values: PrinterForm) {
    const payload = { ...values, ip: values.ip || undefined }
    if (editing) {
      await updatePrinter.mutateAsync({ id: editing.id, locationId: editing.locationId, data: payload })
    } else {
      if (!locationId) return
      await createPrinter.mutateAsync({ ...payload, locationId, active: true })
    }
    setDialogOpen(false)
  }

  async function handleDelete(p: Printer) {
    if (!confirm(`Delete printer "${p.name}"?`)) return
    await deletePrinter.mutateAsync({ id: p.id, locationId: p.locationId })
  }

  // Build a map: categoryId → printerId from existing routes
  const routeMap: Record<string, string> = {}
  for (const r of routes ?? []) routeMap[r.categoryId] = r.printerId

  async function handleRouteChange(categoryId: string, printerId: string) {
    if (!locationId) return
    await setRoute.mutateAsync({ route: { categoryId, printerId }, locationId })
  }

  return (
    <div className="p-6 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Printers</h1>
        <Button onClick={openCreate}>+ Add Printer</Button>
      </div>

      {isLoading && <Spinner />}

      {!isLoading && printers?.length === 0 && (
        <p className="text-muted-foreground">No printers configured yet.</p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {printers?.map((p) => (
          <Card key={p.id} className={!p.active ? 'opacity-60' : ''}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{p.name}</CardTitle>
                <Badge variant={TYPE_VARIANT[p.type as PrinterType]} className="text-xs">
                  {TYPE_LABELS[p.type as PrinterType]}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm text-muted-foreground">
                {p.ip ? `${p.ip}:${p.port}` : `Port ${p.port}`}
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" className="h-7 text-xs" onClick={() => openEdit(p)}>
                  Edit
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 text-xs text-destructive hover:text-destructive"
                  onClick={() => handleDelete(p)}
                >
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Routing section */}
      {(categories?.length ?? 0) > 0 && (printers?.length ?? 0) > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Print Routing</h2>
          <p className="text-sm text-muted-foreground">
            Assign which printer handles each menu category.
          </p>
          <Card>
            <CardContent className="p-4 space-y-3">
              {categories?.map((cat) => (
                <div key={cat.id} className="flex items-center justify-between gap-4">
                  <span className="text-sm font-medium flex-1">{cat.name}</span>
                  <Select
                    className="w-40"
                    value={routeMap[cat.id] ?? ''}
                    onChange={(e) => handleRouteChange(cat.id, e.target.value)}
                  >
                    <option value="">— None —</option>
                    {printers?.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </Select>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit Printer' : 'Add Printer'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1">
              <Label>Name</Label>
              <Input {...register('name')} placeholder="e.g. Kitchen Printer" />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-1">
              <Label>Type</Label>
              <Select {...register('type')}>
                <option value="receipt">Receipt</option>
                <option value="kitchen">Kitchen</option>
                <option value="label">Label</option>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>IP Address (optional)</Label>
              <Input {...register('ip')} placeholder="192.168.1.100" />
            </div>
            <div className="space-y-1">
              <Label>Port</Label>
              <Input type="number" {...register('port')} />
              {errors.port && <p className="text-xs text-destructive">{errors.port.message}</p>}
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createPrinter.isPending || updatePrinter.isPending}>
                {editing ? 'Save' : 'Add'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
