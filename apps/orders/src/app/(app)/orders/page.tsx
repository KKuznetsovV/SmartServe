'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { useOrders, useCreateOrder } from '@/hooks/use-orders'
import { useLocationWs } from '@/hooks/use-ws'
import { useTables } from '@/hooks/use-tables'
import { useAuthStore } from '@/lib/auth-store'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Select } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import type { OrderStatus, OrderChannel } from '@smartserve/types'

const STATUS_VALUES = ['', 'open', 'submitted', 'preparing', 'ready', 'served', 'paid', 'cancelled'] as const

const STATUS_VARIANT: Record<OrderStatus, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  open: 'outline',
  submitted: 'secondary',
  preparing: 'secondary',
  ready: 'default',
  served: 'default',
  paid: 'default',
  split: 'secondary',
  cancelled: 'destructive',
}

const CHANNELS: OrderChannel[] = ['dine_in', 'takeaway', 'delivery', 'online']

export default function OrdersPage() {
  const t = useTranslations('orders')
  const tCommon = useTranslations('common')
  const locationId = useAuthStore((s) => s.activeLocationId)
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [showCreate, setShowCreate] = useState(false)
  const [selectedTableId, setSelectedTableId] = useState<string>('')
  const [channel, setChannel] = useState<OrderChannel>('dine_in')
  const [guestCount, setGuestCount] = useState<string>('')

  const { data: orders, isLoading } = useOrders(locationId, statusFilter || undefined)
  const { data: tables } = useTables(locationId)
  const createOrder = useCreateOrder()

  useLocationWs(locationId)

  const guestCountRequired = channel === 'dine_in'
  const parsedGuestCount = guestCount ? Number(guestCount) : undefined
  const guestCountInvalid = guestCountRequired && (!parsedGuestCount || parsedGuestCount < 1)

  async function handleCreateOrder() {
    if (!locationId) return
    if (guestCountInvalid) return
    await createOrder.mutateAsync({
      locationId,
      tableId: selectedTableId || undefined,
      channel,
      guestCount: parsedGuestCount,
    })
    setShowCreate(false)
    setSelectedTableId('')
    setChannel('dine_in')
    setGuestCount('')
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('title')}</h1>
        <Button onClick={() => setShowCreate((v) => !v)}>+ {t('newOrder')}</Button>
      </div>

      {showCreate && (
        <Card className="p-4 space-y-3 max-w-sm">
          <p className="font-medium text-sm">{t('newOrder')}</p>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">{t('tableOptional')}</label>
            <Select value={selectedTableId} onChange={(e) => setSelectedTableId(e.target.value)}>
              <option value="">{t('noTableOption')}</option>
              {tables?.map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </Select>
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">{t('channelLabel')}</label>
            <Select value={channel} onChange={(e) => setChannel(e.target.value as OrderChannel)}>
              {CHANNELS.map((c) => (
                <option key={c} value={c}>{t(`channel.${c}`)}</option>
              ))}
            </Select>
          </div>
          {guestCountRequired && (
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">{t('guestCountLabel')}</label>
              <Input
                type="number"
                min={1}
                value={guestCount}
                onChange={(e) => setGuestCount(e.target.value)}
                placeholder={t('guestCountPlaceholder')}
              />
            </div>
          )}
          <div className="flex gap-2">
            <Button size="sm" onClick={handleCreateOrder} disabled={createOrder.isPending || guestCountInvalid}>
              {tCommon('create')}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setShowCreate(false)}>
              {tCommon('cancel')}
            </Button>
          </div>
        </Card>
      )}

      {/* Status filter */}
      <div className="flex flex-wrap gap-2">
        {STATUS_VALUES.map((value) => (
          <button
            key={value}
            onClick={() => setStatusFilter(value)}
            className={`px-3 py-1 rounded-full text-sm border transition-colors ${
              statusFilter === value
                ? 'bg-primary text-primary-foreground border-primary'
                : 'bg-background border-border hover:bg-muted'
            }`}
          >
            {value === '' ? t('allStatuses') : t(`status.${value}`)}
          </button>
        ))}
      </div>

      {isLoading && <Spinner />}

      {!isLoading && orders?.length === 0 && (
        <p className="text-muted-foreground">{t('noOrders')}</p>
      )}

      <div className="space-y-2">
        {orders?.map((order) => (
          <Link key={order.id} href={`/orders/${order.id}`}>
            <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-medium">
                      #{order.id.slice(0, 8)}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {order.tableName ?? t(`channel.${order.channel}`)}
                    </span>
                    {order.guestCount != null && (
                      <span className="text-xs text-muted-foreground">
                        {t('guestCount', { count: order.guestCount })}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {new Date(order.createdAt).toLocaleTimeString('he-IL')}
                    {' · '}
                    {t('itemCount', { count: order.items.length })}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-semibold text-sm">
                    ₪{order.total.toFixed(2)}
                  </span>
                  <Badge variant={STATUS_VARIANT[order.status as OrderStatus]}>
                    {t(`status.${order.status}`)}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}
