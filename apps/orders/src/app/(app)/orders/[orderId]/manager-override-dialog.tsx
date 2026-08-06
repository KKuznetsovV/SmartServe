'use client'

import { useEffect, useState } from 'react'
import type { PinStaff } from '@smartserve/types'
import { apiClient } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  locationId: string
  title?: string
  description?: string
  pending?: boolean
  onConfirm: (override: { managerUserId: string; pin: string; reason: string }) => void | Promise<void>
}

/** Collects a manager/owner PIN + reason before an irreversible action (e.g. deleting an
 * item that's already been submitted to the kitchen). */
export function ManagerOverrideDialog({
  open,
  onOpenChange,
  locationId,
  title = 'Manager Approval Required',
  description = 'This order has already been submitted. A manager must approve this change.',
  pending,
  onConfirm,
}: Props) {
  const [managers, setManagers] = useState<PinStaff[]>([])
  const [managerId, setManagerId] = useState('')
  const [pin, setPin] = useState('')
  const [reason, setReason] = useState('')

  useEffect(() => {
    if (!open) return
    setPin('')
    setReason('')
    apiClient.auth
      .pinStaff(locationId)
      .then((staff) => {
        const eligible = staff.filter((s) => s.role === 'owner' || s.role === 'manager')
        setManagers(eligible)
        setManagerId(eligible[0]?.id ?? '')
      })
      .catch(() => setManagers([]))
  }, [open, locationId])

  const canConfirm = !!managerId && pin.trim().length > 0 && reason.trim().length > 0

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">{description}</p>
          {managers.length === 0 ? (
            <p className="text-sm text-destructive">No manager/owner with a PIN found for this location.</p>
          ) : (
            <Select value={managerId} onChange={(e) => setManagerId(e.target.value)}>
              {managers.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.role})
                </option>
              ))}
            </Select>
          )}
          <Input
            type="password"
            inputMode="numeric"
            placeholder="Manager PIN"
            value={pin}
            onChange={(e) => setPin(e.target.value)}
          />
          <Textarea
            placeholder="Reason for this change"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={!canConfirm || pending}
              onClick={() => onConfirm({ managerUserId: managerId, pin, reason: reason.trim() })}
            >
              Confirm
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
