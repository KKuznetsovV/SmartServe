'use client'

import { useEffect, useState } from 'react'
import { useCreatePayment } from '@/hooks/use-payments'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { formatPrice, splitBillByGuest } from '@/lib/utils'
import type { Order, Payment, PaymentMethod } from '@smartserve/types'

const METHODS: { value: PaymentMethod; label: string; icon: string }[] = [
  { value: 'cash', label: 'Cash', icon: '💵' },
  { value: 'card', label: 'Credit Card', icon: '💳' },
  { value: 'tap', label: 'Tap to Pay', icon: '📱' },
  { value: 'mobile', label: 'Mobile Pay', icon: '📲' },
  { value: 'voucher', label: 'Voucher', icon: '🎟️' },
]

const TIP_PERCENT_PRESETS = [10, 15, 18, 20]

type SplitMode = 'full' | 'equal' | 'guest'
type TipMode = 'none' | 'percent' | 'amount' | 'total'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  orderId: string
  order: Order
  payments: Payment[]
  remaining: number
}

export function PaymentDialog({ open, onOpenChange, orderId, order, payments, remaining }: Props) {
  const [splitMode, setSplitMode] = useState<SplitMode>('full')
  const [method, setMethod] = useState<PaymentMethod>('cash')
  const [amount, setAmount] = useState(remaining.toFixed(2))
  const [shareTag, setShareTag] = useState<number | null>(null)
  const [equalWays, setEqualWays] = useState(2)
  const [tipMode, setTipMode] = useState<TipMode>('none')
  const [tipPercent, setTipPercent] = useState(15)
  const [tipAmountInput, setTipAmountInput] = useState('')
  const [tipTotalInput, setTipTotalInput] = useState('')
  const createPayment = useCreatePayment()

  const guestShares = splitBillByGuest(order, payments)

  // Reset to sensible defaults whenever the dialog (re)opens
  useEffect(() => {
    if (!open) return
    setSplitMode('full')
    setAmount(remaining.toFixed(2))
    setShareTag(null)
    setTipMode('none')
    setTipAmountInput('')
    setTipTotalInput('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  function equalShareAmount(shareNumber: number): { total: number; paid: number; remaining: number } {
    const base = Math.floor((order.total / equalWays) * 100) / 100
    const isLast = shareNumber === equalWays
    // The last share absorbs the rounding remainder so shares always sum to the order total exactly.
    const total = isLast ? Math.round((order.total - base * (equalWays - 1)) * 100) / 100 : base
    const paid = payments.filter((p) => p.guestNumber === shareNumber).reduce((sum, p) => sum + p.amount, 0)
    return { total, paid, remaining: Math.max(0, Math.round((total - paid) * 100) / 100) }
  }

  function pickShare(shareNumber: number, shareRemaining: number) {
    setShareTag(shareNumber)
    setAmount(shareRemaining.toFixed(2))
  }

  const baseAmount = parseFloat(amount) || 0
  const tipAmount =
    tipMode === 'none'
      ? 0
      : tipMode === 'percent'
        ? Math.round(((baseAmount * tipPercent) / 100) * 100) / 100
        : tipMode === 'amount'
          ? parseFloat(tipAmountInput) || 0
          : Math.max(0, (parseFloat(tipTotalInput) || 0) - baseAmount)
  const chargeTotal = Math.round((baseAmount + tipAmount) * 100) / 100

  async function handleConfirm() {
    if (isNaN(baseAmount) || baseAmount <= 0) return
    await createPayment.mutateAsync({
      orderId,
      method,
      amount: baseAmount,
      tipAmount,
      guestNumber: shareTag ?? undefined,
    })
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Collect Payment</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Split mode */}
          <div className="space-y-1">
            <Label>How to split</Label>
            <div className="flex gap-2">
              <Button
                type="button"
                size="sm"
                variant={splitMode === 'full' ? 'default' : 'outline'}
                onClick={() => {
                  setSplitMode('full')
                  setShareTag(null)
                  setAmount(remaining.toFixed(2))
                }}
              >
                Full
              </Button>
              <Button
                type="button"
                size="sm"
                variant={splitMode === 'equal' ? 'default' : 'outline'}
                onClick={() => {
                  setSplitMode('equal')
                  setShareTag(null)
                }}
              >
                Split Equally
              </Button>
              {guestShares.length > 0 && (
                <Button
                  type="button"
                  size="sm"
                  variant={splitMode === 'guest' ? 'default' : 'outline'}
                  onClick={() => {
                    setSplitMode('guest')
                    setShareTag(null)
                  }}
                >
                  Per Guest
                </Button>
              )}
            </div>
          </div>

          {splitMode === 'equal' && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label className="shrink-0">Split into</Label>
                <Input
                  type="number"
                  min={2}
                  max={20}
                  className="w-16"
                  value={equalWays}
                  onChange={(e) => setEqualWays(Math.max(2, Math.min(20, Number(e.target.value) || 2)))}
                />
                <span className="text-sm text-muted-foreground">ways</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {Array.from({ length: equalWays }, (_, i) => i + 1).map((shareNumber) => {
                  const share = equalShareAmount(shareNumber)
                  const isPaid = share.remaining <= 0
                  return (
                    <button
                      key={shareNumber}
                      type="button"
                      disabled={isPaid}
                      onClick={() => pickShare(shareNumber, share.remaining)}
                      className={`rounded-lg border p-2 text-xs text-left transition-colors disabled:opacity-50 ${
                        shareTag === shareNumber
                          ? 'border-primary bg-primary/10 font-medium'
                          : 'border-border hover:bg-muted'
                      }`}
                    >
                      <p className="font-medium">Share {shareNumber}</p>
                      <p className="text-muted-foreground">
                        {isPaid ? 'Paid' : `${formatPrice(share.remaining)} due`}
                      </p>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {splitMode === 'guest' && (
            <div className="grid grid-cols-2 gap-2">
              {guestShares.map((share) => {
                const isPaid = share.remaining <= 0
                return (
                  <button
                    key={share.guestNumber}
                    type="button"
                    disabled={isPaid}
                    onClick={() => pickShare(share.guestNumber, share.remaining)}
                    className={`rounded-lg border p-2 text-xs text-left transition-colors disabled:opacity-50 ${
                      shareTag === share.guestNumber
                        ? 'border-primary bg-primary/10 font-medium'
                        : 'border-border hover:bg-muted'
                    }`}
                  >
                    <p className="font-medium">Guest {share.guestNumber}</p>
                    <p className="text-muted-foreground">
                      {isPaid ? 'Paid' : `${formatPrice(share.remaining)} due (est.)`}
                    </p>
                  </button>
                )
              })}
            </div>
          )}

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

          {/* Tip */}
          <div className="space-y-1">
            <Label>Tip</Label>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant={tipMode === 'none' ? 'default' : 'outline'}
                onClick={() => setTipMode('none')}
              >
                No tip
              </Button>
              {TIP_PERCENT_PRESETS.map((p) => (
                <Button
                  key={p}
                  type="button"
                  size="sm"
                  variant={tipMode === 'percent' && tipPercent === p ? 'default' : 'outline'}
                  onClick={() => {
                    setTipMode('percent')
                    setTipPercent(p)
                  }}
                >
                  {p}%
                </Button>
              ))}
              <Button
                type="button"
                size="sm"
                variant={tipMode === 'amount' ? 'default' : 'outline'}
                onClick={() => setTipMode('amount')}
              >
                Amount
              </Button>
              <Button
                type="button"
                size="sm"
                variant={tipMode === 'total' ? 'default' : 'outline'}
                onClick={() => setTipMode('total')}
              >
                Total incl. tip
              </Button>
            </div>
            {tipMode === 'amount' && (
              <Input
                type="number"
                min="0"
                step="0.01"
                placeholder="Tip amount (₪)"
                value={tipAmountInput}
                onChange={(e) => setTipAmountInput(e.target.value)}
              />
            )}
            {tipMode === 'total' && (
              <Input
                type="number"
                min="0"
                step="0.01"
                placeholder="Total the guest will pay, incl. tip (₪)"
                value={tipTotalInput}
                onChange={(e) => setTipTotalInput(e.target.value)}
              />
            )}
            {tipMode !== 'none' && (
              <p className="text-xs text-muted-foreground">
                Tip: {formatPrice(tipAmount)} · Charging {formatPrice(chargeTotal)} total
              </p>
            )}
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={handleConfirm} disabled={createPayment.isPending || baseAmount <= 0}>
              Confirm Payment
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

