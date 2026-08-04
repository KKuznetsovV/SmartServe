'use client'

import { useState } from 'react'
import { useCreatePayment } from '@/hooks/use-payments'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { PaymentMethod } from '@smartserve/types'

const METHODS: { value: PaymentMethod; label: string; icon: string }[] = [
  { value: 'cash', label: 'Cash', icon: '💵' },
  { value: 'card', label: 'Credit Card', icon: '💳' },
  { value: 'tap', label: 'Tap to Pay', icon: '📱' },
  { value: 'mobile', label: 'Mobile Pay', icon: '📲' },
  { value: 'voucher', label: 'Voucher', icon: '🎟️' },
]

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  orderId: string
  remaining: number
}

export function PaymentDialog({ open, onOpenChange, orderId, remaining }: Props) {
  const [method, setMethod] = useState<PaymentMethod>('cash')
  const [amount, setAmount] = useState(remaining.toFixed(2))
  const createPayment = useCreatePayment()

  // Sync amount when remaining changes (e.g. dialog reopens)
  function handleOpen(isOpen: boolean) {
    if (isOpen) setAmount(remaining.toFixed(2))
    onOpenChange(isOpen)
  }

  async function handleConfirm() {
    const parsed = parseFloat(amount)
    if (isNaN(parsed) || parsed <= 0) return
    await createPayment.mutateAsync({ orderId, method, amount: parsed })
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpen}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Collect Payment</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Method grid */}
          <div className="space-y-1">
            <Label>Payment method</Label>
            <div className="grid grid-cols-3 gap-2">
              {METHODS.map((m) => (
                <button
                  key={m.value}
                  type="button"
                  onClick={() => setMethod(m.value)}
                  className={`flex flex-col items-center gap-1 rounded-lg border p-3 text-xs transition-colors ${
                    method === m.value
                      ? 'border-primary bg-primary/10 text-primary font-medium'
                      : 'border-border hover:bg-muted'
                  }`}
                >
                  <span className="text-xl">{m.icon}</span>
                  {m.label}
                </button>
              ))}
            </div>
          </div>

          {/* Amount */}
          <div className="space-y-1">
            <Label>Amount (₪)</Label>
            <Input
              type="number"
              min="0.01"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">Balance due: ₪{remaining.toFixed(2)}</p>
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={handleConfirm} disabled={createPayment.isPending}>
              Confirm Payment
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
