'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'
import type { DisplayOrder } from '@smartserve/types'
import { apiClient } from '@/lib/api'
import { useDeviceStore } from '@/lib/device-store'
import { useAuthReady } from '@/hooks/use-auth-ready'
import { useLocationWs } from '@/hooks/use-ws'
import { playReadyChime } from './chime'
import { newlyReadyNumbers, splitDisplayOrders } from './columns'

export default function CustomerDisplayPage() {
  const router = useRouter()
  const t = useTranslations('display')
  const { ready, deviceConfigured } = useAuthReady()
  const locationId = useDeviceStore((s) => s.locationId)
  const deviceToken = useDeviceStore((s) => s.deviceToken)
  const deviceType = useDeviceStore((s) => s.deviceType)
  const seenReady = useRef<Set<number>>(new Set())
  const primed = useRef(false)
  const [flash, setFlash] = useState<Set<number>>(new Set())

  useEffect(() => {
    if (ready && (!deviceConfigured || deviceType !== 'display')) {
      router.replace('/setup')
    }
  }, [ready, deviceConfigured, deviceType, router])

  const { data: orders = [], dataUpdatedAt } = useQuery({
    queryKey: ['orders', locationId, 'display'],
    queryFn: () => apiClient.orders.publicDisplay(deviceToken as string),
    enabled: Boolean(deviceToken && deviceType === 'display'),
    refetchInterval: 15_000,
  })

  useLocationWs(deviceType === 'display' ? locationId : null)

  const { preparing, ready: readyOrders } = splitDisplayOrders(orders)
  const lastUpdated = dataUpdatedAt ? new Date(dataUpdatedAt) : new Date()

  useEffect(() => {
    const numbers = newlyReadyNumbers(seenReady.current, readyOrders)
    const next = new Set(
      readyOrders.map((order) => order.orderNumber).filter((n): n is number => n != null),
    )
    if (!primed.current) {
      primed.current = true
      seenReady.current = next
      return
    }
    seenReady.current = next
    if (numbers.length === 0) return
    playReadyChime()
    setFlash(new Set(numbers))
    const timer = window.setTimeout(() => setFlash(new Set()), 4000)
    return () => window.clearTimeout(timer)
  }, [readyOrders])

  if (!ready || !deviceConfigured || deviceType !== 'display') {
    return null
  }

  return (
    <main className="min-h-screen bg-zinc-950 px-6 py-6 text-white">
      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">{t('title')}</h1>
        <p className="text-sm text-zinc-400">
          {t('updated', { time: lastUpdated.toLocaleTimeString() })}
        </p>
      </div>

      <div className="grid min-h-[70vh] grid-cols-1 gap-6 lg:grid-cols-2">
        <DisplayColumn
          testId="display-preparing"
          title={t('preparing')}
          empty={t('noPreparing')}
          orders={preparing}
          tone="preparing"
          flash={flash}
        />
        <DisplayColumn
          testId="display-ready"
          title={t('ready')}
          empty={t('noReady')}
          orders={readyOrders}
          tone="ready"
          flash={flash}
        />
      </div>
    </main>
  )
}

function DisplayColumn({
  testId,
  title,
  empty,
  orders,
  tone,
  flash,
}: {
  testId: string
  title: string
  empty: string
  orders: DisplayOrder[]
  tone: 'preparing' | 'ready'
  flash: ReadonlySet<number>
}) {
  const panel =
    tone === 'ready'
      ? 'border-emerald-500/40 bg-emerald-950/40'
      : 'border-amber-500/40 bg-amber-950/30'
  return (
    <section
      data-testid={testId}
      className={`flex min-h-[20rem] flex-col rounded-3xl border-2 p-6 ${panel}`}
    >
      <h2 className="mb-6 text-center text-3xl font-semibold uppercase tracking-wide">{title}</h2>
      {orders.length === 0 ? (
        <p className="m-auto text-xl text-zinc-400">{empty}</p>
      ) : (
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {orders.map((order) => {
            const n = order.orderNumber
            const lit = n != null && flash.has(n)
            return (
              <li
                key={`${order.orderNumber}-${order.updatedAt}`}
                data-testid="display-number"
                data-order-number={order.orderNumber ?? ''}
                className={`flex min-h-32 items-center justify-center rounded-2xl px-3 py-4 font-mono text-[clamp(3.5rem,8vw,7rem)] font-black leading-none ${
                  tone === 'ready' ? 'bg-emerald-500 text-emerald-950' : 'bg-amber-500 text-amber-950'
                } ${lit ? 'animate-pulse ring-4 ring-white' : ''}`}
              >
                {order.orderNumber}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
