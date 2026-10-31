'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { MapPin } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { toast } from 'sonner'
import type { DeviceType, Location } from '@smartserve/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { apiClient } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { useDeviceStore } from '@/lib/device-store'
import { useAuthReady } from '@/hooks/use-auth-ready'
import { LocaleToggle } from '@/components/layout/locale-toggle'
import { ThemeToggle } from '@/components/layout/theme-toggle'

export default function SetupPage() {
  const router = useRouter()
  const t = useTranslations('setup')
  const { ready, deviceConfigured } = useAuthReady()
  const setDevice = useDeviceStore((s) => s.setDevice)
  const setTokens = useAuthStore((s) => s.setTokens)
  const clearAuth = useAuthStore((s) => s.clearAuth)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [locations, setLocations] = useState<Location[]>([])
  const [locationId, setLocationId] = useState('')
  const [deviceName, setDeviceName] = useState('')
  const [deviceType, setDeviceType] = useState<DeviceType>('pos')
  const [step, setStep] = useState<'login' | 'device'>('login')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (ready && deviceConfigured) {
      router.replace('/login')
    }
  }, [ready, deviceConfigured, router])

  const onLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    try {
      const tokens = await apiClient.auth.login(email.trim(), password)
      setTokens(tokens.accessToken, tokens.refreshToken)
      const user = await apiClient.auth.me()
      const listed = await apiClient.locations.list(user.businessId)
      if (!listed.length) {
        toast.error(t('noLocations'))
        clearAuth()
        return
      }
      setLocations(listed)
      setLocationId(listed[0].id)
      setStep('device')
    } catch {
      toast.error(t('invalidCredentials'))
      clearAuth()
    } finally {
      setBusy(false)
    }
  }

  const onRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!locationId || !deviceName.trim()) return
    setBusy(true)
    try {
      const registered = await apiClient.auth.registerDevice(locationId, {
        name: deviceName.trim(),
        type: deviceType,
      })
      setDevice({
        locationId,
        deviceToken: registered.token,
        deviceType,
        deviceName: registered.name,
      })
      clearAuth()
      router.push('/login')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('registerFailed'))
    } finally {
      setBusy(false)
    }
  }

  if (!ready || deviceConfigured) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
      <div className="absolute end-4 top-4 flex items-center gap-2">
        <LocaleToggle />
        <ThemeToggle />
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
          {step === 'login' ? (
            <form onSubmit={onLogin} className="space-y-4">
              <div className="space-y-1">
                <Label htmlFor="email">{t('email')}</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="username"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="password">{t('password')}</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" className="w-full" disabled={busy}>
                {busy ? <Spinner /> : t('continue')}
              </Button>
            </form>
          ) : (
            <form onSubmit={onRegister} className="space-y-4">
              <div className="space-y-1">
                <Label htmlFor="location">{t('location')}</Label>
                <Select
                  id="location"
                  value={locationId}
                  onChange={(e) => setLocationId(e.target.value)}
                >
                  {locations.map((loc) => (
                    <option key={loc.id} value={loc.id}>
                      {loc.name}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="deviceName">{t('deviceName')}</Label>
                <Input
                  id="deviceName"
                  value={deviceName}
                  onChange={(e) => setDeviceName(e.target.value)}
                  placeholder={t('deviceNamePlaceholder')}
                  required
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="deviceType">{t('deviceType')}</Label>
                <Select
                  id="deviceType"
                  value={deviceType}
                  onChange={(e) => setDeviceType(e.target.value as DeviceType)}
                >
                  <option value="pos">{t('typePos')}</option>
                  <option value="kds">{t('typeKds')}</option>
                  <option value="display">{t('typeDisplay')}</option>
                </Select>
              </div>
              <Button type="submit" className="w-full" disabled={busy}>
                {busy ? <Spinner /> : t('saveContinue')}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
