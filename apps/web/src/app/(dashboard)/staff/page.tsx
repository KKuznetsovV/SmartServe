'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useStaff, useCreateStaff, useUpdateStaff } from '@/hooks/use-staff'
import { useTranslations } from 'next-intl'
import { useAuthStore } from '@/lib/auth-store'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { assignableRoles, type User, type UserRole } from '@smartserve/types'

const ROLE_VARIANT: Record<UserRole, 'default' | 'secondary' | 'outline'> = {
  owner: 'default',
  manager: 'default',
  cashier: 'secondary',
  waiter: 'secondary',
  kitchen: 'outline',
}

const createSchema = z.object({
  name: z.string().min(1, 'Required'),
  email: z.string().email().optional().or(z.literal('')),
  role: z.enum(['owner', 'manager', 'cashier', 'waiter', 'kitchen']),
  language: z.enum(['he', 'en']),
  active: z.boolean().optional(),
  password: z.string().min(8).optional().or(z.literal('')),
  pin: z.string().regex(/^\d{4,6}$/, 'Must be 4 to 6 digits').optional().or(z.literal('')),
})

const editSchema = createSchema.omit({ password: true }).extend({
  pin: z.string().regex(/^\d{4,6}$/, 'Must be 4 to 6 digits').optional().or(z.literal('')),
})

type CreateForm = z.infer<typeof createSchema>
type EditForm = z.infer<typeof editSchema>

export default function StaffPage() {
  const t = useTranslations('staff')
  const tCommon = useTranslations('common')
  const activeBusinessId = useAuthStore((s) => s.activeBusinessId)
  const currentUser = useAuthStore((s) => s.user)
  const pickerRoles = assignableRoles((currentUser?.role as UserRole | undefined) ?? 'waiter')
  const { data: staff, isLoading } = useStaff(activeBusinessId)
  const createStaff = useCreateStaff()
  const updateStaff = useUpdateStaff()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<User | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateForm>({ resolver: zodResolver(editing ? editSchema : createSchema) })

  function openCreate() {
    setEditing(null)
    const defaultRole = pickerRoles.includes('waiter') ? 'waiter' : (pickerRoles[0] ?? 'waiter')
    reset({ name: '', email: '', role: defaultRole, language: 'he', password: '', pin: '' })
    setDialogOpen(true)
  }

  function openEdit(u: User) {
    setEditing(u)
    reset({ name: u.name, email: u.email ?? '', role: u.role, language: u.language, active: u.active, pin: '' })
    setDialogOpen(true)
  }

  function canDeactivate(u: User) {
    if (!currentUser) return false
    if (u.id === currentUser.id) return false
    if (u.role === 'owner' && currentUser.role === 'manager') return false
    return true
  }

  function toggleActive(u: User) {
    if (!canDeactivate(u)) return
    updateStaff.mutate({ id: u.id, businessId: u.businessId, data: { active: !u.active } })
  }

  async function onSubmit(values: CreateForm) {
    const clean = {
      ...values,
      email: values.email || undefined,
      password: values.password || undefined,
      pin: values.pin || undefined,
    }

    if (editing) {
      const { password: _pw, role, active, ...rest } = clean
      const editData: Partial<User> & { pin?: string } = { ...rest }
      if (role !== editing.role) {
        editData.role = role
      }
      if (canDeactivate(editing) && active !== undefined) {
        editData.active = active
      }
      await updateStaff.mutateAsync({ id: editing.id, businessId: editing.businessId, data: editData })
    } else {
      if (!activeBusinessId) return
      await createStaff.mutateAsync({ ...clean, businessId: activeBusinessId, active: true })
    }
    setDialogOpen(false)
  }

  const activeStaff = (staff ?? []).filter((u) => u.active)
  const inactiveStaff = (staff ?? []).filter((u) => !u.active)

  function renderStaffCard(u: User) {
    return (
      <Card key={u.id} className={!u.active ? 'opacity-50' : ''}>
        <CardContent className="p-4 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium">{u.name}</span>
              <Badge variant={ROLE_VARIANT[u.role as UserRole]} className="text-xs">
                {t(`role_${u.role}` as `role_${UserRole}`)}
              </Badge>
              {!u.active && (
                <Badge variant="outline" className="text-xs">{t('inactive')}</Badge>
              )}
            </div>
            {u.email && (
              <p className="text-sm text-muted-foreground mt-0.5">{u.email}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {canDeactivate(u) && (
              <Button
                variant="ghost"
                size="sm"
                className={u.active ? 'text-destructive hover:text-destructive' : ''}
                disabled={updateStaff.isPending}
                onClick={() => toggleActive(u)}
              >
                {u.active ? t('deactivate') : t('reactivate')}
              </Button>
            )}
            <Button variant="outline" size="sm" onClick={() => openEdit(u)}>
              {tCommon('edit')}
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('title')}</h1>
        <Button onClick={openCreate}>+ {t('addStaff')}</Button>
      </div>

      {isLoading && <Spinner />}

      {!isLoading && staff?.length === 0 && (
        <p className="text-muted-foreground">{t('noStaff')}</p>
      )}

      {!isLoading && staff && staff.length > 0 && (
        <div className="space-y-6">
          <div className="space-y-2">
            <h2 className="text-sm font-medium text-muted-foreground">{t('activeCount', { count: activeStaff.length })}</h2>
            {activeStaff.length === 0 && (
              <p className="text-sm text-muted-foreground">{t('noActiveStaff')}</p>
            )}
            {activeStaff.map(renderStaffCard)}
          </div>

          {inactiveStaff.length > 0 && (
            <div className="space-y-2">
              <h2 className="text-sm font-medium text-muted-foreground">{t('inactiveCount', { count: inactiveStaff.length })}</h2>
              {inactiveStaff.map(renderStaffCard)}
            </div>
          )}
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>{editing ? t('editStaffMember') : t('addStaffMember')}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1">
              <Label>{t('name')}</Label>
              <Input {...register('name')} placeholder={t('fullNamePlaceholder')} />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>

            <div className="space-y-1">
              <Label>{t('emailOptional')}</Label>
              <Input type="email" {...register('email')} placeholder="name@example.com" />
              {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>{t('role')}</Label>
                <Select {...register('role')}>
                  {(editing && !pickerRoles.includes(editing.role as UserRole)
                    ? [editing.role as UserRole, ...pickerRoles]
                    : pickerRoles
                  ).map((r) => (
                    <option key={r} value={r}>
                      {t(`role_${r}` as `role_${UserRole}`)}
                    </option>
                  ))}
                </Select>
                {errors.role && <p className="text-xs text-destructive">{errors.role.message}</p>}
              </div>
              <div className="space-y-1">
                <Label>{t('preferredLanguage')}</Label>
                <Select {...register('language')}>
                  <option value="he">עברית</option>
                  <option value="en">English</option>
                </Select>
              </div>
            </div>

            {!editing && (
              <div className="space-y-1">
                <Label>{t('passwordOptional')}</Label>
                <Input type="password" {...register('password')} placeholder={t('passwordMinCharsPlaceholder')} />
                {errors.password && (
                  <p className="text-xs text-destructive">{errors.password.message}</p>
                )}
              </div>
            )}

            <div className="space-y-1">
              <Label>{editing ? t('pinEditHint') : t('pinCreateHint')}</Label>
              <Input
                type="password"
                maxLength={6}
                inputMode="numeric"
                {...register('pin')}
                placeholder="····"
              />
              {errors.pin && <p className="text-xs text-destructive">{errors.pin.message}</p>}
            </div>

            {editing && canDeactivate(editing) && (
              <div className="flex items-center gap-2">
                <input type="checkbox" id="active" {...register('active')} />
                <Label htmlFor="active">{t('active')}</Label>
              </div>
            )}

            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                {tCommon('cancel')}
              </Button>
              <Button type="submit" disabled={createStaff.isPending || updateStaff.isPending}>
                {editing ? tCommon('save') : tCommon('add')}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
