'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { toast } from 'sonner'
import { ChefHat, Lock } from 'lucide-react'
import { useTranslations } from 'next-intl'
import type { PinStaff } from '@smartserve/types'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { safeInternalPath } from '@smartserve/ui'
import { apiClient } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { useDeviceStore } from '@/lib/device-store'
import { useAuthReady } from '@/hooks/use-auth-ready'
import { LocaleToggle } from '@/components/layout/locale-toggle'
import { ThemeToggle } from '@/components/layout/theme-toggle'
import { PinPad } from '@/components/pin-pad'

const PIN_LENGTH = 4

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <Spinner />
        </div>
      }
    >
      <LoginForm />
    </Suspense>
  )
}

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const t = useTranslations('auth')
  const tCommon = useTranslations('common')
  const tRoles = useTranslations('roles')
  const { ready, authenticated, deviceConfigured } = useAuthReady()
  const locationId = useDeviceStore((s) => s.locationId)
  const deviceToken = useDeviceStore((s) => s.deviceToken)
  const clearDevice = useDeviceStore((s) => s.clearDevice)
  const setAuth = useAuthStore((s) => s.setAuth)
  const setTokens = useAuthStore((s) => s.setTokens)
  const setActiveLocation = useAuthStore((s) => s.setActiveLocation)
  const afterLogin = safeInternalPath(searchParams.get('next'), '/orders')

  const [staff, setStaff] = useState<PinStaff[]>([])
  const [loadingStaff, setLoadingStaff] = useState(true)
  const [selected, setSelected] = useState<PinStaff | null>(null)
  const [pin, setPin] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!ready) return
    if (!deviceConfigured) {
      router.replace('/setup')
      return
    }
    if (authenticated) {
      router.replace(afterLogin)
    }
  }, [ready, deviceConfigured, authenticated, afterLogin, router])

  useEffect(() => {
    if (!ready || !deviceConfigured || !locationId || !deviceToken || authenticated) return
    apiClient.auth
      .pinStaff(locationId, deviceToken)
      .then(setStaff)
      .catch(() => toast.error(t('failedLoadStaff')))
      .finally(() => setLoadingStaff(false))
  }, [ready, deviceConfigured, locationId, deviceToken, authenticated, router, t])

  if (!ready || !deviceConfigured || authenticated || !locationId || !deviceToken) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner />
      </div>
    )
  }

  const submitPin = async (value: string) => {
    if (!selected) return
    setSubmitting(true)
    try {
      const tokens = await apiClient.auth.pinLogin(locationId, selected.id, value, deviceToken)
      setTokens(tokens.accessToken)
      const user = await apiClient.auth.me()
      setAuth(tokens.accessToken, user)
      setActiveLocation(user.businessId, locationId)
      router.push(afterLogin)
    } catch {
      toast.error(t('invalidPin'))
      setPin('')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDigit = (digit: string) => {
    if (submitting) return
    setPin((current) => {
      if (current.length >= PIN_LENGTH) return current
      const next = current + digit
      if (next.length === PIN_LENGTH) void submitPin(next)
      return next
    })
  }

  if (!selected) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center bg-muted/40 p-4">
        <div className="absolute end-4 top-4 flex items-center gap-2">
          <LocaleToggle className="h-12 min-h-12 min-w-12" />
          <ThemeToggle className="h-12 min-h-12 w-12 min-w-12" />
        </div>
        <div className="mb-6 flex items-center gap-2">
          <ChefHat className="h-6 w-6 text-primary" />
          <h1 className="text-xl font-semibold">SmartServe</h1>
        </div>
        {loadingStaff ? (
          <Spinner />
        ) : (
          <div className="grid w-full max-w-2xl grid-cols-2 gap-3 sm:grid-cols-3">
            {staff.map((member) => (
              <button
                key={member.id}
                onClick={() => setSelected(member)}
                className="flex min-h-12 flex-col items-center gap-2 rounded-lg border bg-card p-4 text-center transition hover:border-primary hover:bg-accent"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-lg font-semibold text-primary">
                  {member.name.charAt(0).toUpperCase()}
                </div>
                <span className="font-medium">{member.name}</span>
                <span className="text-xs capitalize text-muted-foreground">
                  {tRoles.has(member.role) ? tRoles(member.role) : member.role}
                </span>
              </button>
            ))}
            {staff.length === 0 && (
              <p className="col-span-full text-sm text-muted-foreground">{t('noStaffFound')}</p>
            )}
          </div>
        )}
        <Button
          variant="ghost"
          className="mt-6 text-xs"
          onClick={() => {
            clearDevice()
            router.push('/setup')
          }}
        >
          {t('changeLocation')}
        </Button>
      </main>
    )
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-muted/40 p-4">
      <Card className="w-full max-w-xs">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Lock className="h-6 w-6 text-primary" />
          </div>
          <h1 className="text-lg font-semibold leading-none tracking-tight">{selected.name}</h1>
          <p className="text-sm capitalize text-muted-foreground">
            {tRoles.has(selected.role) ? tRoles(selected.role) : selected.role}
          </p>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4">
          <PinPad
            pinLength={PIN_LENGTH}
            pin={pin}
            disabled={submitting}
            backLabel={tCommon('back')}
            deleteLabel={t('deleteDigit')}
            onDigit={handleDigit}
            onEnter={() => {
              if (pin.length === PIN_LENGTH) void submitPin(pin)
            }}
            onBackspace={() => setPin((p) => p.slice(0, -1))}
            onBack={() => {
              setSelected(null)
              setPin('')
            }}
          />
          {submitting && <Spinner />}
        </CardContent>
      </Card>
    </main>
  )
}
