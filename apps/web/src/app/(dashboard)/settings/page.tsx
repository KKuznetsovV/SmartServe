'use client'

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
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
})
type BizForm = z.infer<typeof bizSchema>

const locSchema = z.object({
  name: z.string().min(1, 'Required'),
  address: z.string().optional().or(z.literal('')),
  timezone: z.string().min(1),
  language: z.enum(['he', 'en']),
})
type LocForm = z.infer<typeof locSchema>

const CURRENCIES = ['ILS', 'USD', 'EUR', 'GBP']
const TIMEZONES = ['Asia/Jerusalem', 'Europe/London', 'America/New_York', 'America/Los_Angeles', 'Europe/Paris']

export default function SettingsPage() {
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
    mutationFn: (data: BizForm) => apiClient.businesses.update(activeBusinessId!, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['business', activeBusinessId] })
      toast.success('Business settings saved')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const updateLoc = useMutation({
    mutationFn: (data: LocForm) => apiClient.locations.update(activeLocationId!, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['location', activeLocationId] })
      toast.success('Location settings saved')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const bizForm = useForm<BizForm>({ resolver: zodResolver(bizSchema) })
  const locForm = useForm<LocForm>({ resolver: zodResolver(locSchema) })

  useEffect(() => {
    if (biz) bizForm.reset({ name: biz.name, taxId: biz.taxId ?? '', currency: biz.currency })
  }, [biz]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (loc)
      locForm.reset({
        name: loc.name,
        address: loc.address ?? '',
        timezone: loc.timezone,
        language: loc.language as 'he' | 'en',
      })
  }, [loc]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="p-6 space-y-8 max-w-xl">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* Business */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Business</CardTitle>
        </CardHeader>
        <CardContent>
          {bizLoading && <Spinner />}
          {!bizLoading && (
            <form onSubmit={bizForm.handleSubmit((v) => updateBiz.mutate(v))} className="space-y-4">
              <div className="space-y-1">
                <Label>Business name</Label>
                <Input {...bizForm.register('name')} />
                {bizForm.formState.errors.name && (
                  <p className="text-xs text-destructive">{bizForm.formState.errors.name.message}</p>
                )}
              </div>
              <div className="space-y-1">
                <Label>Tax ID (optional)</Label>
                <Input {...bizForm.register('taxId')} placeholder="e.g. 512345678" />
              </div>
              <div className="space-y-1">
                <Label>Currency</Label>
                <Select {...bizForm.register('currency')}>
                  {CURRENCIES.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </Select>
              </div>
              <Button type="submit" disabled={updateBiz.isPending}>Save Business</Button>
            </form>
          )}
        </CardContent>
      </Card>

      {/* Location */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Location</CardTitle>
        </CardHeader>
        <CardContent>
          {locLoading && <Spinner />}
          {!locLoading && (
            <form onSubmit={locForm.handleSubmit((v) => updateLoc.mutate(v))} className="space-y-4">
              <div className="space-y-1">
                <Label>Location name</Label>
                <Input {...locForm.register('name')} />
                {locForm.formState.errors.name && (
                  <p className="text-xs text-destructive">{locForm.formState.errors.name.message}</p>
                )}
              </div>
              <div className="space-y-1">
                <Label>Address (optional)</Label>
                <Input {...locForm.register('address')} placeholder="Street, City" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label>Timezone</Label>
                  <Select {...locForm.register('timezone')}>
                    {TIMEZONES.map((tz) => (
                      <option key={tz} value={tz}>{tz}</option>
                    ))}
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label>Language</Label>
                  <Select {...locForm.register('language')}>
                    <option value="he">עברית</option>
                    <option value="en">English</option>
                  </Select>
                </div>
              </div>
              <Button type="submit" disabled={updateLoc.isPending}>Save Location</Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
