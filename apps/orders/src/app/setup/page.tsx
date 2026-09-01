'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { MapPin } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useDeviceStore } from '@/lib/device-store'
import { LocaleToggle } from '@/components/layout/locale-toggle'

export default function SetupPage() {
  const router = useRouter()
  const t = useTranslations('setup')
  const locationId = useDeviceStore((s) => s.locationId)
  const setLocationId = useDeviceStore((s) => s.setLocationId)
  const [value, setValue] = useState(locationId ?? '')

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!value.trim()) return
    setLocationId(value.trim())
    router.push('/login')
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
      <div className="absolute end-4 top-4">
        <LocaleToggle />
      </div>
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <MapPin className="h-6 w-6 text-primary" />
          </div>
          <CardTitle className="text-2xl">{t('title')}</CardTitle>
          <p className="text-sm text-muted-foreground">{t('description')}</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="locationId">{t('locationIdLabel')}</Label>
              <Input
                id="locationId"
                placeholder="00000000-0000-0000-0000-000000000000"
                value={value}
                onChange={(e) => setValue(e.target.value)}
              />
            </div>
            <Button type="submit" className="w-full">
              {t('saveContinue')}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
