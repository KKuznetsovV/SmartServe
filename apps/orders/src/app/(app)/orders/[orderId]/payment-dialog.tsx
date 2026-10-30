'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { useCreatePayment } from '@/hooks/use-payments'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { formatPrice, splitBillByGuest } from '@/lib/utils'
import type { Order, Payment, PaymentMethod } from '@smartserve/types'

const METHODS: { value: PaymentMethod; key: string; icon: string }[] = [
  { value: 'cash', key: 'cash', icon: '💵' },
  { value: 'card', key: 'card', icon: '💳' },
  { value: 'tap', key: 'tap', icon: '📱' },
  { value: 'mobile', key: 'mobile', icon: '📲' },
  { value: 'voucher', key: 'voucher', icon: '🎟️' },
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
  const t = useTranslations('paymentDialog')
  const tPaymentMethod = useTranslations('paymentMethod')
  const tCommon = useTranslations('common')
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
    const result = await createPayment.mutateAsync({
      orderId,
      method,
      amount: baseAmount,
      tipAmount,
      guestNumber: shareTag ?? undefined,
    })
    if (result.remaining != null) {
      setAmount(result.remaining.toFixed(2))
    }
    if (result.orderFullyPaid || (result.remaining ?? remaining) <= 0) {
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{t('title')}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Split mode */}
          <div className="space-y-1">
            <Label>{t('howToSplit')}</Label>
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
                {t('full')}
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
                {t('splitEqually')}
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
                  {t('perGuest')}
                </Button>
              )}
            </div>
          </div>

          {splitMode === 'equal' && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Label className="shrink-0">{t('splitInto')}</Label>
                <Input
                  type="number"
                  min={2}
                  max={20}
                  className="w-16"
                  value={equalWays}
                  onChange={(e) => setEqualWays(Math.max(2, Math.min(20, Number(e.target.value) || 2)))}
                />
                <span className="text-sm text-muted-foreground">{t('ways')}</span>
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
                      className={`rounded-lg border p-2 text-xs text-start transition-colors disabled:opacity-50 ${
                        shareTag === shareNumber
                          ? 'border-primary bg-primary/10 font-medium'
                          : 'border-border hover:bg-muted'
                      }`}
                    >
                      <p className="font-medium">{t('share', { number: shareNumber })}</p>
                      <p className="text-muted-foreground">
                        {isPaid ? t('paid') : t('due', { amount: formatPrice(share.remaining) })}
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
                    className={`rounded-lg border p-2 text-xs text-start transition-colors disabled:opacity-50 ${
                      shareTag === share.guestNumber
                        ? 'border-primary bg-primary/10 font-medium'
                        : 'border-border hover:bg-muted'
                    }`}
                  >
                    <p className="font-medium">{t('guest', { number: share.guestNumber })}</p>
                    <p className="text-muted-foreground">
                      {isPaid ? t('paid') : t('dueEstimate', { amount: formatPrice(share.remaining) })}
                    </p>
                  </button>
                )
              })}
            </div>
          )}

          {/* Method grid */}
          <div className="space-y-1">
            <Label>{t('paymentMethodLabel')}</Label>
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
                  {tPaymentMethod(m.key)}
                </button>
              ))}
            </div>
          </div>

          {/* Amount */}
          <div className="space-y-1">
            <Label>{t('amount')}</Label>
            <Input
              type="number"
              min="0.01"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">{t('balanceDue', { amount: remaining.toFixed(2) })}</p>
          </div>

          {/* Tip */}
          <div className="space-y-1">
            <Label>{t('tip')}</Label>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                size="sm"
                variant={tipMode === 'none' ? 'default' : 'outline'}
                onClick={() => setTipMode('none')}
              >
                {t('noTip')}
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
                {t('customAmount')}
              </Button>
              <Button
                type="button"
                size="sm"
                variant={tipMode === 'total' ? 'default' : 'outline'}
                onClick={() => setTipMode('total')}
              >
                {t('totalInclTip')}
              </Button>
            </div>
            {tipMode === 'amount' && (
              <Input
                type="number"
                min="0"
                step="0.01"
                placeholder={t('tipAmountPlaceholder')}
                value={tipAmountInput}
                onChange={(e) => setTipAmountInput(e.target.value)}
              />
            )}
            {tipMode === 'total' && (
              <Input
                type="number"
                min="0"
                step="0.01"
                placeholder={t('tipTotalPlaceholder')}
                value={tipTotalInput}
                onChange={(e) => setTipTotalInput(e.target.value)}
              />
            )}
            {tipMode !== 'none' && (
              <p className="text-xs text-muted-foreground">
                {t('tipSummary', { tip: formatPrice(tipAmount), total: formatPrice(chargeTotal) })}
              </p>
            )}
          </div>

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              {tCommon('cancel')}
            </Button>
            <Button onClick={handleConfirm} disabled={createPayment.isPending || baseAmount <= 0}>
              {t('confirmPayment')}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

