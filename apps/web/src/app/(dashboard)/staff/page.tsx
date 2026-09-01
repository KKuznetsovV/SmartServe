'use client'

import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Search } from 'lucide-react'
import { useStaff, useCreateStaff, useUpdateStaff } from '@/hooks/use-staff'
import { useAuthStore } from '@/lib/auth-store'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import type { User, UserRole } from '@smartserve/types'

const ROLES: UserRole[] = ['owner', 'manager', 'cashier', 'waiter', 'kitchen']
const ACTIVE_FILTER_OPTIONS = [
  { value: 'all', label: 'All' },
  { value: 'active', label: 'Active only' },
  { value: 'inactive', label: 'Inactive only' },
] as const
type ActiveFilter = (typeof ACTIVE_FILTER_OPTIONS)[number]['value']

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
  pin: z.string().length(4).regex(/^\d{4}$/, 'Must be 4 digits').optional().or(z.literal('')),
})

const editSchema = createSchema.omit({ password: true }).extend({
  pin: z.string().length(4).regex(/^\d{4}$/, 'Must be 4 digits').optional().or(z.literal('')),
})

type CreateForm = z.infer<typeof createSchema>
type EditForm = z.infer<typeof editSchema>

export default function StaffPage() {
  const activeBusinessId = useAuthStore((s) => s.activeBusinessId)
  const { data: staff, isLoading } = useStaff(activeBusinessId)
  const createStaff = useCreateStaff()
  const updateStaff = useUpdateStaff()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<User | null>(null)

  const [nameFilter, setNameFilter] = useState('')
  const [roleFilter, setRoleFilter] = useState<UserRole | 'all'>('all')
  const [activeFilter, setActiveFilter] = useState<ActiveFilter>('all')

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateForm>({ resolver: zodResolver(editing ? editSchema : createSchema) })

  function openCreate() {
    setEditing(null)
    reset({ name: '', email: '', role: 'waiter', language: 'he', password: '', pin: '' })
    setDialogOpen(true)
  }

  function openEdit(u: User) {
    setEditing(u)
    reset({ name: u.name, email: u.email ?? '', role: u.role, language: u.language, active: u.active, pin: '' })
    setDialogOpen(true)
  }

  function toggleActive(u: User) {
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
      const { password: _pw, ...editData } = clean
      await updateStaff.mutateAsync({ id: editing.id, businessId: editing.businessId, data: editData })
    } else {
      if (!activeBusinessId) return
      await createStaff.mutateAsync({ ...clean, businessId: activeBusinessId, active: true })
    }
    setDialogOpen(false)
  }

  const filteredStaff = useMemo(() => {
    const query = nameFilter.trim().toLowerCase()
    return (staff ?? []).filter((u) => {
      if (query && !u.name.toLowerCase().includes(query)) return false
      if (roleFilter !== 'all' && u.role !== roleFilter) return false
      if (activeFilter === 'active' && !u.active) return false
      if (activeFilter === 'inactive' && u.active) return false
      return true
    })
  }, [staff, nameFilter, roleFilter, activeFilter])

  const hasFilters = nameFilter.trim() !== '' || roleFilter !== 'all' || activeFilter !== 'all'
  const filteredActiveStaff = filteredStaff.filter((u) => u.active)
  const filteredInactiveStaff = filteredStaff.filter((u) => !u.active)

  function renderStaffCard(u: User) {
    return (
      <Card key={u.id} className={!u.active ? 'opacity-50' : ''}>
        <CardContent className="p-4 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-medium">{u.name}</span>
              <Badge variant={ROLE_VARIANT[u.role as UserRole]} className="text-xs capitalize">
                {u.role}
              </Badge>
              {!u.active && (
                <Badge variant="outline" className="text-xs">Inactive</Badge>
              )}
            </div>
            {u.email && (
              <p className="text-sm text-muted-foreground mt-0.5">{u.email}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              className={u.active ? 'text-destructive hover:text-destructive' : ''}
              disabled={updateStaff.isPending}
              onClick={() => toggleActive(u)}
            >
              {u.active ? 'Deactivate' : 'Reactivate'}
            </Button>
            <Button variant="outline" size="sm" onClick={() => openEdit(u)}>
              Edit
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Staff</h1>
        <Button onClick={openCreate}>+ Add Staff</Button>
      </div>

      {isLoading && <Spinner />}

      {!isLoading && staff?.length === 0 && (
        <p className="text-muted-foreground">No staff members yet.</p>
      )}

      {!isLoading && staff && staff.length > 0 && (
        <>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <div className="flex-1 space-y-1">
              <Label htmlFor="staff-search">Search by name</Label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="staff-search"
                  value={nameFilter}
                  onChange={(e) => setNameFilter(e.target.value)}
                  placeholder="Search staff by name…"
                  className="pl-8"
                  aria-label="Search staff by name"
                />
              </div>
            </div>
            <div className="space-y-1 sm:w-40">
              <Label htmlFor="staff-role-filter">Position</Label>
              <Select
                id="staff-role-filter"
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value as UserRole | 'all')}
                aria-label="Filter by position"
              >
                <option value="all">All positions</option>
                {ROLES.map((r) => (
                  <option key={r} value={r} className="capitalize">
                    {r}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-1 sm:w-40">
              <Label htmlFor="staff-active-filter">Status</Label>
              <Select
                id="staff-active-filter"
                value={activeFilter}
                onChange={(e) => setActiveFilter(e.target.value as ActiveFilter)}
                aria-label="Filter by active status"
              >
                {ACTIVE_FILTER_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <p className="text-sm text-muted-foreground" role="status" aria-live="polite">
            {hasFilters
              ? `${filteredStaff.length} of ${staff.length} staff member${staff.length !== 1 ? 's' : ''} match`
              : `${staff.length} staff member${staff.length !== 1 ? 's' : ''}`}
          </p>

          {filteredStaff.length === 0 ? (
            <p className="text-muted-foreground">No staff members match your filters.</p>
          ) : (
            <div className="space-y-6">
              <div className="space-y-2">
                <h2 className="text-sm font-medium text-muted-foreground">
                  Active ({filteredActiveStaff.length})
                </h2>
                {filteredActiveStaff.length === 0 && (
                  <p className="text-sm text-muted-foreground">No active staff members match your filters.</p>
                )}
                {filteredActiveStaff.map(renderStaffCard)}
              </div>

              {filteredInactiveStaff.length > 0 && (
                <div className="space-y-2">
                  <h2 className="text-sm font-medium text-muted-foreground">
                    Inactive ({filteredInactiveStaff.length})
                  </h2>
                  {filteredInactiveStaff.map(renderStaffCard)}
                </div>
              )}
            </div>
          )}
        </>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit Staff Member' : 'Add Staff Member'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1">
              <Label>Name</Label>
              <Input {...register('name')} placeholder="Full name" />
              {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
            </div>

            <div className="space-y-1">
              <Label>Email (optional)</Label>
              <Input type="email" {...register('email')} placeholder="name@example.com" />
              {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>Role</Label>
                <Select {...register('role')}>
                  {ROLES.map((r) => (
                    <option key={r} value={r} className="capitalize">
                      {r}
                    </option>
                  ))}
                </Select>
                {errors.role && <p className="text-xs text-destructive">{errors.role.message}</p>}
              </div>
              <div className="space-y-1">
                <Label>Language</Label>
                <Select {...register('language')}>
                  <option value="he">עברית</option>
                  <option value="en">English</option>
                </Select>
              </div>
            </div>

            {!editing && (
              <div className="space-y-1">
                <Label>Password (optional)</Label>
                <Input type="password" {...register('password')} placeholder="Min 8 chars" />
                {errors.password && (
                  <p className="text-xs text-destructive">{errors.password.message}</p>
                )}
              </div>
            )}

            <div className="space-y-1">
              <Label>PIN {editing ? '(leave blank to keep)' : '(optional, 4 digits)'}</Label>
              <Input
                type="password"
                maxLength={4}
                inputMode="numeric"
                {...register('pin')}
                placeholder="····"
              />
              {errors.pin && <p className="text-xs text-destructive">{errors.pin.message}</p>}
            </div>

            {editing && (
              <div className="flex items-center gap-2">
                <input type="checkbox" id="active" {...register('active')} />
                <Label htmlFor="active">Active</Label>
              </div>
            )}

            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createStaff.isPending || updateStaff.isPending}>
                {editing ? 'Save' : 'Add'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
