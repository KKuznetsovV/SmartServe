'use client'

import { useState } from 'react'
import { useLocale, useTranslations } from 'next-intl'
import { useAuthStore } from '@/lib/auth-store'
import { useCurrentShift, useShiftHistory, useOpenShift, useCloseShift } from '@/hooks/use-shifts'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'

function formatDuration(from: string, to: string | undefined, hourAbbrev: string, minuteAbbrev: string) {
  const start = new Date(from)
  const end = to ? new Date(to) : new Date()
  const mins = Math.floor((end.getTime() - start.getTime()) / 60_000)
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return h > 0 ? `${h}${hourAbbrev} ${m}${minuteAbbrev}` : `${m}${minuteAbbrev}`
}

export default function ShiftsPage() {
  const t = useTranslations('shifts')
  const locale = useLocale()
  const dateLocale = locale === 'he' ? 'he-IL' : 'en-US'
  const activeLocationId = useAuthStore((s) => s.activeLocationId)
  const { data: current, isLoading } = useCurrentShift(activeLocationId)
  const { data: history } = useShiftHistory(activeLocationId)
  const openShift = useOpenShift()
  const closeShift = useCloseShift()

  const [openingCash, setOpeningCash] = useState('0')
  const [closingCash, setClosingCash] = useState('0')

  if (isLoading) {
    return (
      <div className="p-6">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold">{t('title')}</h1>

      {/* Current shift */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">{t('currentShift')}</CardTitle>
            <Badge variant={current ? 'success' : 'outline'}>
              {current ? t('open') : t('noShiftOpen')}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {current ? (
            <>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">{t('opened')}</p>
                  <p className="font-medium">{new Date(current.openedAt).toLocaleTimeString(dateLocale)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{t('duration')}</p>
                  <p className="font-medium">{formatDuration(current.openedAt, undefined, t('hourAbbrev'), t('minuteAbbrev'))}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">{t('openingCash')}</p>
                  <p className="font-medium">₪{current.openingCash.toFixed(2)}</p>
                </div>
              </div>
              <div className="space-y-2 pt-2 border-t">
                <Label htmlFor="closing-cash">{t('closingCashCount')}</Label>
                <div className="flex gap-2">
                  <Input
                    id="closing-cash"
                    type="number"
                    min="0"
                    step="0.01"
                    value={closingCash}
                    onChange={(e) => setClosingCash(e.target.value)}
                    className="max-w-xs"
                  />
                  <Button
                    variant="destructive"
                    disabled={closeShift.isPending}
                    onClick={() =>
                      closeShift.mutate({
                        shiftId: current.id,
                        locationId: activeLocationId!,
                        closingCash: parseFloat(closingCash) || 0,
                      })
                    }
                  >
                    {t('closeShift')}
                  </Button>
                </div>
                {current.openingCash > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {t('expectedCashDrift', { amount: (parseFloat(closingCash) - current.openingCash).toFixed(2) })}
                  </p>
                )}
              </div>
            </>
          ) : (
            <div className="space-y-2">
              <Label htmlFor="opening-cash">{t('openingCashFloat')}</Label>
              <div className="flex gap-2">
                <Input
                  id="opening-cash"
                  type="number"
                  min="0"
                  step="0.01"
                  value={openingCash}
                  onChange={(e) => setOpeningCash(e.target.value)}
                  className="max-w-xs"
                />
                <Button
                  disabled={openShift.isPending}
                  onClick={() =>
                    openShift.mutate({
                      locationId: activeLocationId!,
                      openingCash: parseFloat(openingCash) || 0,
                    })
                  }
                >
                  {t('openShift')}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Shift history */}
      {history && history.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">{t('recentShifts')}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {history.map((s) => (
              <div key={s.id} className="flex items-center justify-between py-2 border-b last:border-0 text-sm">
                <div className="space-y-0.5">
                  <p className="font-medium">{new Date(s.openedAt).toLocaleDateString(dateLocale)}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(s.openedAt).toLocaleTimeString(dateLocale)}
                    {s.closedAt && ` → ${new Date(s.closedAt).toLocaleTimeString(dateLocale)}`}
                    {s.closedAt && ` · ${formatDuration(s.openedAt, s.closedAt, t('hourAbbrev'), t('minuteAbbrev'))}`}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {s.closingCash != null && (
                    <span className="text-muted-foreground">
                      ₪{s.openingCash.toFixed(0)} → ₪{s.closingCash.toFixed(0)}
                    </span>
                  )}
                  <Badge variant={s.status === 'open' ? 'success' : 'secondary'}>
                    {s.status === 'open' ? t('open') : t('closed')}
                  </Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
