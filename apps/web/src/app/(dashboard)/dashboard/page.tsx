'use client'

import Link from 'next/link'
import { useOrders } from '@/hooks/use-orders'
import { useReportSummary } from '@/hooks/use-reports'
import { useAuthStore } from '@/lib/auth-store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import type { OrderStatus } from '@smartserve/types'

// The orders/tables screens live in the separate `orders` app (different port/origin), not this app.
const ORDERS_APP_URL = process.env.NEXT_PUBLIC_ORDERS_URL ?? 'http://localhost:3001'

const ACTIVE_STATUSES: OrderStatus[] = ['open', 'submitted', 'preparing', 'ready']

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

const STATUS_COLOR: Record<OrderStatus, string> = {
  open: 'text-slate-600',
  submitted: 'text-blue-600',
  preparing: 'text-amber-600',
  ready: 'text-green-600',
  served: 'text-green-700',
  paid: 'text-green-800',
  split: 'text-slate-600',
  cancelled: 'text-red-500',
}

export default function DashboardPage() {
  const locationId = useAuthStore((s) => s.activeLocationId)
  const user = useAuthStore((s) => s.user)

  const { data: allOrders, isLoading } = useOrders(locationId)
  const { data: report } = useReportSummary(locationId, 'today')

  // Count active orders by status
  const countByStatus = (allOrders ?? []).reduce<Partial<Record<OrderStatus, number>>>(
    (acc, o) => {
      const s = o.status as OrderStatus
      acc[s] = (acc[s] ?? 0) + 1
      return acc
    },
    {},
  )

  const activeOrders = (allOrders ?? []).filter((o) =>
    (ACTIVE_STATUSES as string[]).includes(o.status),
  )

  const recentOrders = (allOrders ?? [])
    .slice()
    .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
    .slice(0, 8)

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">
          {user ? `Welcome back, ${user.name.split(' ')[0]}` : 'Dashboard'}
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          {new Date().toLocaleDateString('he-IL', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })}
        </p>
      </div>

      {/* Today KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Revenue today
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">₪{(report?.totalRevenue ?? 0).toFixed(0)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Paid orders
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{report?.orderCount ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Avg order
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">₪{(report?.avgOrderValue ?? 0).toFixed(0)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Active now
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{activeOrders.length}</p>
          </CardContent>
        </Card>
      </div>

      {/* Live order status breakdown */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {ACTIVE_STATUSES.map((s) => (
          <a key={s} href={`${ORDERS_APP_URL}/orders?status=${s}`}>
            <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
              <CardContent className="p-4 text-center">
                <p className={`text-3xl font-bold ${STATUS_COLOR[s]}`}>
                  {countByStatus[s] ?? 0}
                </p>
                <p className="text-xs text-muted-foreground capitalize mt-1">{s}</p>
              </CardContent>
            </Card>
          </a>
        ))}
      </div>

      {/* Quick actions */}
      <div className="flex flex-wrap gap-3">
        <a href={`${ORDERS_APP_URL}/orders`}>
          <Button>New Order</Button>
        </a>
        <a href={`${ORDERS_APP_URL}/tables`}>
          <Button variant="outline">Floor Plan</Button>
        </a>
        <Link href="/menu">
          <Button variant="outline">Menu</Button>
        </Link>
        <Link href="/reports">
          <Button variant="outline">Reports</Button>
        </Link>
      </div>

      {/* Recent orders */}
      <div className="space-y-2">
        <h2 className="text-base font-semibold">Recent Orders</h2>

        {isLoading && <Spinner />}

        {!isLoading && recentOrders.length === 0 && (
          <p className="text-sm text-muted-foreground">No orders yet today.</p>
        )}

        {recentOrders.map((o) => (
          <a key={o.id} href={`${ORDERS_APP_URL}/orders/${o.id}`}>
            <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
              <CardContent className="p-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-muted-foreground">
                    #{o.id.slice(0, 8)}
                  </span>
                  {o.tableName && <span className="text-sm">{o.tableName}</span>}
                  <span className="text-xs text-muted-foreground capitalize">
                    {o.channel.replace('_', ' ')}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground">
                    {new Date(o.createdAt).toLocaleTimeString('he-IL', {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                  <span className="text-sm font-medium">₪{o.total.toFixed(0)}</span>
                  <Badge variant={STATUS_VARIANT[o.status as OrderStatus]} className="text-xs capitalize">
                    {o.status}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </a>
        ))}
      </div>
    </div>
  )
}
