'use client'

import { useAuthStore } from '@/lib/auth-store'
import { useLocationStock, useSetStock } from '@/hooks/use-stock'
import { useLocale, useTranslations } from 'next-intl'
import { formatPrice, localizedName } from '@smartserve/ui'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'

export default function StockPage() {
  const t = useTranslations('stock')
  const locale = useLocale()
  const activeLocationId = useAuthStore((s) => s.activeLocationId)
  const { data: items, isLoading } = useLocationStock(activeLocationId)
  const setStock = useSetStock()

  const inStock = (items ?? []).filter((i) => i.inStock)
  const outOfStock = (items ?? []).filter((i) => !i.inStock)

  if (isLoading) {
    return (
      <div className="p-6">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold">{t('title')}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {t('summary', { inCount: inStock.length, outCount: outOfStock.length })}
        </p>
      </div>

      {outOfStock.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base text-destructive">{t('outOfStockTitle')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {outOfStock.map((item) => (
              <div key={item.id} className="flex items-center justify-between py-2 border-b last:border-0">
                <div>
                  <p className="text-sm font-medium">{localizedName(item, locale)}</p>
                  <p className="text-xs text-muted-foreground">{formatPrice(item.price)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="destructive">{t('outOfStockTitle')}</Badge>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={setStock.isPending}
                    onClick={() =>
                      setStock.mutate({ id: item.id, locationId: activeLocationId!, inStock: true })
                    }
                  >
                    {t('markInStock')}
                  </Button>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t('inStockTitle', { count: inStock.length })}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {inStock.length === 0 && (
            <p className="text-sm text-muted-foreground">{t('noInStock')}</p>
          )}
          {inStock.map((item) => (
            <div key={item.id} className="flex items-center justify-between py-2 border-b last:border-0">
              <div>
                <p className="text-sm font-medium">{localizedName(item, locale)}</p>
                <p className="text-xs text-muted-foreground">{formatPrice(item.price)}</p>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="success">{t('inStockBadge')}</Badge>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-destructive hover:text-destructive hover:bg-destructive/10"
                  disabled={setStock.isPending}
                  onClick={() =>
                    setStock.mutate({ id: item.id, locationId: activeLocationId!, inStock: false })
                  }
                >
                  {t('markOut')}
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
