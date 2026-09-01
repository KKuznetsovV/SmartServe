'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Trash2, ToggleLeft, ToggleRight, Plus } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { useAuthStore } from '@/lib/auth-store'
import { useDiscounts, useCreateDiscount, useUpdateDiscount, useDeleteDiscount } from '@/hooks/use-discounts'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'

const schema = z.object({
  code: z.string().min(1).max(50).toUpperCase(),
  name: z.string().min(1),
  type: z.enum(['percent', 'fixed']),
  value: z.coerce.number().positive(),
  minOrderAmount: z.coerce.number().min(0).default(0),
  expiresAt: z.string().optional().or(z.literal('')),
})
type FormData = z.infer<typeof schema>

export default function DiscountsPage() {
  const t = useTranslations('discounts')
  const tCommon = useTranslations('common')
  const businessId = useAuthStore((s) => s.activeBusinessId)
  const [showForm, setShowForm] = useState(false)

  const { data: discounts = [], isLoading } = useDiscounts(businessId)
  const createMutation = useCreateDiscount()
  const updateMutation = useUpdateDiscount()
  const deleteMutation = useDeleteDiscount()

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { type: 'percent', minOrderAmount: 0 } })

  const discountType = watch('type')

  async function onSubmit(data: FormData) {
    if (!businessId) return
    await createMutation.mutateAsync({
      businessId,
      code: data.code,
      name: data.name,
      type: data.type,
      value: data.value,
      minOrderAmount: data.minOrderAmount,
      active: true,
      expiresAt: data.expiresAt || undefined,
    })
    reset()
    setShowForm(false)
  }

  if (isLoading) return <Spinner />

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('title')}</h1>
        <Button onClick={() => setShowForm((v) => !v)} size="sm">
          <Plus className="me-1 size-4" />
          {t('newDiscount')}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>{t('createDiscount')}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <Label>{t('code')}</Label>
                <Input {...register('code')} placeholder="SUMMER20" className="uppercase" />
                {errors.code && <p className="text-xs text-red-500">{errors.code.message}</p>}
              </div>

              <div className="space-y-1">
                <Label>{t('name')}</Label>
                <Input {...register('name')} placeholder="Summer Sale" />
                {errors.name && <p className="text-xs text-red-500">{errors.name.message}</p>}
              </div>

              <div className="space-y-1">
                <Label>{t('type')}</Label>
                <select
                  {...register('type')}
                  className="border-input bg-background h-9 w-full rounded-md border px-3 text-sm"
                >
                  <option value="percent">{t('type_percent')}</option>
                  <option value="fixed">{t('type_fixed')}</option>
                </select>
              </div>

              <div className="space-y-1">
                <Label>{t('value')} {discountType === 'percent' ? '(%)' : '(amount)'}</Label>
                <Input {...register('value')} type="number" step="0.01" placeholder={discountType === 'percent' ? '10' : '5.00'} />
                {errors.value && <p className="text-xs text-red-500">{errors.value.message}</p>}
              </div>

              <div className="space-y-1">
                <Label>{t('minOrderAmount')}</Label>
                <Input {...register('minOrderAmount')} type="number" step="0.01" placeholder="0" />
              </div>

              <div className="space-y-1">
                <Label>{t('expiresAtOptional')}</Label>
                <Input {...register('expiresAt')} type="datetime-local" />
              </div>

              <div className="flex gap-2 sm:col-span-2">
                <Button type="submit" disabled={isSubmitting}>
                  {isSubmitting ? t('creating') : tCommon('create')}
                </Button>
                <Button type="button" variant="outline" onClick={() => { reset(); setShowForm(false) }}>
                  {tCommon('cancel')}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {discounts.length === 0 && !showForm && (
        <p className="text-muted-foreground text-sm">{t('noDiscounts')}</p>
      )}

      <div className="grid gap-3">
        {discounts.map((d) => (
          <Card key={d.id}>
            <CardContent className="flex items-center justify-between py-4">
              <div className="flex items-center gap-4">
                <div>
                  <p className="font-mono font-semibold tracking-wide">{d.code}</p>
                  <p className="text-muted-foreground text-sm">{d.name}</p>
                </div>
                <Badge variant={d.type === 'percent' ? 'secondary' : 'outline'}>
                  {d.type === 'percent' ? `${d.value}%` : t('off', { value: d.value })}
                </Badge>
                {d.minOrderAmount > 0 && (
                  <span className="text-muted-foreground text-xs">{t('minOrder', { amount: d.minOrderAmount })}</span>
                )}
                {d.expiresAt && (
                  <span className="text-muted-foreground text-xs">
                    {t('expires', { date: new Date(d.expiresAt).toLocaleDateString() })}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <Badge variant={d.active ? 'success' : 'secondary'}>{d.active ? t('active') : t('inactive')}</Badge>
                <Button
                  size="icon"
                  variant="ghost"
                  title={d.active ? t('deactivate') : t('activate')}
                  onClick={() =>
                    updateMutation.mutate({ id: d.id, businessId: d.businessId, data: { active: !d.active } })
                  }
                >
                  {d.active ? <ToggleRight className="size-4 text-emerald-500" /> : <ToggleLeft className="size-4" />}
                </Button>
                <Button
                  size="icon"
                  variant="ghost"
                  title={tCommon('delete')}
                  onClick={() => deleteMutation.mutate({ id: d.id, businessId: d.businessId })}
                >
                  <Trash2 className="size-4 text-red-500" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
