'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useLocale, useTranslations } from 'next-intl'
import { localizedName } from '@smartserve/ui'
import {
  usePrinters,
  usePrinterRoutes,
  useCreatePrinter,
  useUpdatePrinter,
  useDeletePrinter,
  useAddPrinterRoute,
  useDeletePrinterRoute,
} from '@/hooks/use-printers'
import { useCategories } from '@/hooks/use-menu'
import { useLocationStock } from '@/hooks/use-stock'
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
  const t = useTranslations('printers')
  const tCommon = useTranslations('common')
  const locale = useLocale()
  const locationId = useAuthStore((s) => s.activeLocationId)
  const { data: printers, isLoading } = usePrinters(locationId)
  const { data: routes } = usePrinterRoutes(locationId)
  const { data: categories } = useCategories(locationId)
  const { data: items } = useLocationStock(locationId)
  const createPrinter = useCreatePrinter()
  const updatePrinter = useUpdatePrinter()
  const deletePrinter = useDeletePrinter()
  const addRoute = useAddPrinterRoute()
  const deleteRoute = useDeletePrinterRoute()

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
    if (!confirm(t('confirmDelete', { name: p.name }))) return
    await deletePrinter.mutateAsync({ id: p.id, locationId: p.locationId })
  }

  // Build a map: `${itemId}:${printerId}` → routeId from existing routes, for O(1) lookup
  const routeIdByKey: Record<string, string> = {}
  for (const r of routes ?? []) routeIdByKey[`${r.itemId}:${r.printerId}`] = r.id

  async function handleRouteToggle(itemId: string, printerId: string, checked: boolean) {
    if (!locationId) return
    if (checked) {
      await addRoute.mutateAsync({ printerId, itemId, locationId })
    } else {
      const routeId = routeIdByKey[`${itemId}:${printerId}`]
      if (routeId) await deleteRoute.mutateAsync({ routeId, locationId })
    }
  }

  // Group items by category, so routing is shown per-item within its category
  const itemsByCategory = new Map<string, NonNullable<typeof items>>()
  for (const item of items ?? []) {
    const list = itemsByCategory.get(item.categoryId) ?? []
    list.push(item)
    itemsByCategory.set(item.categoryId, list)
  }

  return (
    <div className="p-6 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('title')}</h1>
        <Button onClick={openCreate}>+ {t('addPrinter')}</Button>
      </div>

      {isLoading && <Spinner />}

      {!isLoading && printers?.length === 0 && (
        <p className="text-muted-foreground">{t('noPrinters')}</p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {printers?.map((p) => (
          <Card key={p.id} className={!p.active ? 'opacity-60' : ''}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{p.name}</CardTitle>
                <Badge variant={TYPE_VARIANT[p.type as PrinterType]} className="text-xs">
                  {t(`type_${p.type}` as 'type_receipt' | 'type_kitchen' | 'type_label')}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm text-muted-foreground">
                {p.ip ? `${p.ip}:${p.port}` : `${t('port')} ${p.port}`}
              </p>
              <div className="flex gap-2">
                <Button variant="outline" className="min-h-12" onClick={() => openEdit(p)}>
                  {tCommon('edit')}
                </Button>
                <Button
                  variant="outline"
                  className="min-h-12 text-destructive hover:text-destructive"
                  onClick={() => handleDelete(p)}
                >
                  {tCommon('delete')}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Routing section */}
      {(items?.length ?? 0) > 0 && (printers?.length ?? 0) > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">{t('routingTitle')}</h2>
          <p className="text-sm text-muted-foreground">
            {t('routingHint')}
          </p>
          <Card>
            <CardContent className="p-4 space-y-6">
              {categories
                ?.filter((cat) => (itemsByCategory.get(cat.id)?.length ?? 0) > 0)
                .map((cat) => (
                  <div key={cat.id} className="space-y-2">
                    <h3 className="text-sm font-semibold text-muted-foreground">{localizedName(cat, locale)}</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-start text-xs text-muted-foreground">
                            <th className="py-1 pe-4 font-medium">{t('item')}</th>
                            {printers?.map((p) => (
                              <th key={p.id} className="py-1 px-2 font-medium text-center whitespace-nowrap">
                                {p.name}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {itemsByCategory.get(cat.id)?.map((item) => (
                            <tr key={item.id} className="border-t">
                              <td className="py-1.5 pe-4">{localizedName(item, locale)}</td>
                              {printers?.map((p) => (
                                <td key={p.id} className="py-1.5 px-2 text-center">
                                  <input
                                    type="checkbox"
                                    className="h-12 w-12 accent-primary"
                                    aria-label={t('routeTo', {
                                      item: localizedName(item, locale),
                                      printer: p.name,
                                    })}
                                    checked={!!routeIdByKey[`${item.id}:${p.id}`]}
                                    onChange={(e) => handleRouteToggle(item.id, p.id, e.target.checked)}
                                  />
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
            </CardContent>
          </Card>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>{editing ? t('editPrinter') : t('addPrinter')}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="printer-name">{t('name')}</Label>
              <Input id="printer-name" {...register('name')} placeholder="e.g. Kitchen Printer" />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>
            <div className="space-y-1">
              <Label htmlFor="printer-type">{t('type')}</Label>
              <Select id="printer-type" {...register('type')}>
                <option value="receipt">{t('type_receipt')}</option>
                <option value="kitchen">{t('type_kitchen')}</option>
                <option value="label">{t('type_label')}</option>
              </Select>
            </div>
            <div className="space-y-1">
              <Label htmlFor="printer-ip">{t('ipAddressOptional')}</Label>
              <Input id="printer-ip" {...register('ip')} placeholder="192.168.1.100" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="printer-port">{t('port')}</Label>
              <Input id="printer-port" type="number" {...register('port')} />
              {errors.port && <p className="text-xs text-destructive">{errors.port.message}</p>}
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" className="min-h-12" onClick={() => setDialogOpen(false)}>
                {tCommon('cancel')}
              </Button>
              <Button className="min-h-12" type="submit" disabled={createPrinter.isPending || updatePrinter.isPending}>
                {editing ? tCommon('save') : tCommon('add')}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
