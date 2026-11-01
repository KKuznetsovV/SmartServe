'use client'

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useTranslations } from 'next-intl'
import { useAuthStore } from '@/lib/auth-store'
import { apiClient } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'

const bizSchema = z.object({
  name: z.string().min(1, 'Required'),
  taxId: z.string().optional().or(z.literal('')),
  currency: z.string().min(1),
  vatRatePercent: z.coerce.number().min(0).max(100),
})
type BizForm = z.infer<typeof bizSchema>

const locSchema = z.object({
  name: z.string().min(1, 'Required'),
  address: z.string().optional().or(z.literal('')),
  timezone: z.string().min(1),
  businessDayCutoff: z.string().regex(/^\d{2}:\d{2}$/),
  language: z.enum(['he', 'en']),
  vatRatePercent: z.string(),
})
type LocForm = z.infer<typeof locSchema>

const CURRENCIES = ['ILS', 'USD', 'EUR', 'GBP']
const TIMEZONES = ['Asia/Jerusalem', 'Europe/London', 'America/New_York', 'America/Los_Angeles', 'Europe/Paris']

export default function SettingsPage() {
  const t = useTranslations('settings')
  const qc = useQueryClient()
  const activeBusinessId = useAuthStore((s) => s.activeBusinessId)
  const activeLocationId = useAuthStore((s) => s.activeLocationId)

  const { data: biz, isLoading: bizLoading } = useQuery({
    queryKey: ['business', activeBusinessId],
    queryFn: () => apiClient.businesses.get(activeBusinessId!),
    enabled: !!activeBusinessId,
  })

  const { data: loc, isLoading: locLoading } = useQuery({
    queryKey: ['location', activeLocationId],
    queryFn: () => apiClient.locations.get(activeLocationId!),
    enabled: !!activeLocationId,
  })

  const updateBiz = useMutation({
    mutationFn: (data: BizForm) =>
      apiClient.businesses.update(activeBusinessId!, {
        name: data.name,
        taxId: data.taxId,
        currency: data.currency,
        vatRate: data.vatRatePercent / 100,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['business', activeBusinessId] })
      toast.success(t('businessSaved'))
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const updateLoc = useMutation({
    mutationFn: (data: LocForm) => {
      const trimmed = data.vatRatePercent.trim()
      return apiClient.locations.update(activeLocationId!, {
        name: data.name,
        address: data.address,
        timezone: data.timezone,
        businessDayCutoff: data.businessDayCutoff,
        language: data.language,
        vatRate: trimmed === '' ? null : Number(trimmed) / 100,
      })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['location', activeLocationId] })
      toast.success(t('locationSaved'))
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const bizForm = useForm<BizForm>({ resolver: zodResolver(bizSchema) })
  const locForm = useForm<LocForm>({ resolver: zodResolver(locSchema) })

  useEffect(() => {
    if (biz)
      bizForm.reset({
        name: biz.name,
        taxId: biz.taxId ?? '',
        currency: biz.currency,
        vatRatePercent: Math.round((biz.vatRate ?? 0.18) * 1000) / 10,
      })
  }, [biz]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (loc)
      locForm.reset({
        name: loc.name,
        address: loc.address ?? '',
        timezone: loc.timezone,
        businessDayCutoff: (loc.businessDayCutoff ?? '05:00:00').slice(0, 5),
        language: loc.language as 'he' | 'en',
        vatRatePercent: loc.vatRate == null ? '' : String(Math.round(loc.vatRate * 1000) / 10),
      })
  }, [loc]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="p-6 space-y-8 max-w-xl">
      <h1 className="text-2xl font-bold">{t('title')}</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t('business')}</CardTitle>
        </CardHeader>
        <CardContent>
          {bizLoading && <Spinner />}
          {!bizLoading && (
            <form onSubmit={bizForm.handleSubmit((v) => updateBiz.mutate(v))} className="space-y-4">
              <div className="space-y-1">
                <Label htmlFor="biz-name">{t('businessName')}</Label>
                <Input id="biz-name" {...bizForm.register('name')} />
                {bizForm.formState.errors.name && (
                  <p className="text-xs text-destructive">{bizForm.formState.errors.name.message}</p>
                )}
              </div>
              <div className="space-y-1">
                <Label htmlFor="biz-tax">{t('taxIdOptional')}</Label>
                <Input id="biz-tax" {...bizForm.register('taxId')} placeholder="e.g. 512345678" />
              </div>
              <div className="space-y-1">
                <Label htmlFor="biz-currency">{t('currency')}</Label>
                <Select id="biz-currency" {...bizForm.register('currency')}>
                  {CURRENCIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </Select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="biz-vat">{t('vatRate')}</Label>
                <Input id="biz-vat" type="number" step="0.1" min={0} max={100} {...bizForm.register('vatRatePercent')} />
                <p className="text-xs text-muted-foreground">{t('vatRateHint')}</p>
              </div>
              <Button type="submit" disabled={updateBiz.isPending}>{t('saveBusiness')}</Button>
            </form>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t('location')}</CardTitle>
        </CardHeader>
        <CardContent>
          {locLoading && <Spinner />}
          {!locLoading && (
            <form onSubmit={locForm.handleSubmit((v) => updateLoc.mutate(v))} className="space-y-4">
              <div className="space-y-1">
                <Label htmlFor="loc-name">{t('locationName')}</Label>
                <Input id="loc-name" {...locForm.register('name')} />
                {locForm.formState.errors.name && (
                  <p className="text-xs text-destructive">{locForm.formState.errors.name.message}</p>
                )}
              </div>
              <div className="space-y-1">
                <Label htmlFor="loc-address">{t('addressOptional')}</Label>
                <Input id="loc-address" {...locForm.register('address')} placeholder={t('addressPlaceholder')} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label htmlFor="loc-timezone">{t('timezone')}</Label>
                  <Select id="loc-timezone" {...locForm.register('timezone')}>
                    {TIMEZONES.map((tz) => (
                      <option key={tz} value={tz}>{tz}</option>
                    ))}
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="loc-language">{t('defaultLanguage')}</Label>
                  <Select id="loc-language" {...locForm.register('language')}>
                    <option value="he">עברית</option>
                    <option value="en">English</option>
                  </Select>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">{t('defaultLanguageHint')}</p>
              <div className="space-y-1">
                <Label htmlFor="loc-cutoff">{t('businessDayCutoff')}</Label>
                <Input id="loc-cutoff" type="time" {...locForm.register('businessDayCutoff')} />
                <p className="text-xs text-muted-foreground">{t('businessDayCutoffHint')}</p>
              </div>
              <div className="space-y-1">
                <Label htmlFor="loc-vat">{t('locationVatRate')}</Label>
                <Input
                  id="loc-vat"
                  type="number"
                  step="0.1"
                  min={0}
                  max={100}
                  placeholder="18"
                  {...locForm.register('vatRatePercent')}
                />
                <p className="text-xs text-muted-foreground">{t('locationVatRateHint')}</p>
              </div>
              <Button type="submit" disabled={updateLoc.isPending}>{t('saveLocation')}</Button>
            </form>
          )}
        </CardContent>
      </Card>

      <DevicesCard locationId={activeLocationId} />
    </div>
  )
}

function DevicesCard({ locationId }: { locationId: string | null }) {
  const t = useTranslations('settings')
  const qc = useQueryClient()
  const { data: devices, isLoading } = useQuery({
    queryKey: ['devices', locationId],
    queryFn: () => apiClient.auth.listDevices(locationId!),
    enabled: !!locationId,
  })
  const revoke = useMutation({
    mutationFn: (deviceId: string) => apiClient.auth.revokeDevice(deviceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['devices', locationId] })
      toast.success(t('deviceRevoked'))
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t('devices')}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading && <Spinner />}
        {!isLoading && (!devices || devices.length === 0) && (
          <p className="text-sm text-muted-foreground">{t('noDevices')}</p>
        )}
        {(devices ?? []).map((device) => (
          <div key={device.id} className="flex items-center justify-between gap-3 rounded-md border px-3 py-2">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{device.name}</p>
              <p className="text-xs text-muted-foreground">
                {device.type}
                {device.revokedAt ? ' · ' + t('revoked') : ''}
              </p>
            </div>
            {!device.revokedAt && (
              <Button
                size="sm"
                variant="outline"
                disabled={revoke.isPending}
                onClick={() => revoke.mutate(device.id)}
              >
                {t('revokeDevice')}
              </Button>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
