'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { ChefHat, Lock, Delete } from 'lucide-react'
import type { PinStaff } from '@smartserve/types'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { apiClient } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { useDeviceStore } from '@/lib/device-store'

const PIN_LENGTH = 4

export default function LoginPage() {
  const router = useRouter()
  const locationId = useDeviceStore((s) => s.locationId)
  const setAuth = useAuthStore((s) => s.setAuth)
  const setTokens = useAuthStore((s) => s.setTokens)
  const setActiveLocation = useAuthStore((s) => s.setActiveLocation)

  const [staff, setStaff] = useState<PinStaff[]>([])
  const [loadingStaff, setLoadingStaff] = useState(true)
  const [selected, setSelected] = useState<PinStaff | null>(null)
  const [pin, setPin] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!locationId) {
      router.replace('/setup')
      return
    }
    apiClient.auth
      .pinStaff(locationId)
      .then(setStaff)
      .catch(() => toast.error('Failed to load staff list'))
      .finally(() => setLoadingStaff(false))
  }, [locationId, router])

  if (!locationId) return null

  const submitPin = async (value: string) => {
    if (!selected) return
    setSubmitting(true)
    try {
      const tokens = await apiClient.auth.pinLogin(locationId, value)
      setTokens(tokens.accessToken, tokens.refreshToken)
      const user = await apiClient.auth.me()
      if (user.id !== selected.id) {
        throw new Error('PIN does not match selected user')
      }
      setAuth(tokens.accessToken, tokens.refreshToken, user)
      setActiveLocation(user.businessId, locationId)
      router.push('/orders')
    } catch {
      toast.error('Invalid PIN')
      setPin('')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDigit = (digit: string) => {
    if (submitting) return
    const next = (pin + digit).slice(0, PIN_LENGTH)
    setPin(next)
    if (next.length === PIN_LENGTH) void submitPin(next)
  }

  if (!selected) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-muted/40 p-4">
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
                className="flex flex-col items-center gap-2 rounded-lg border bg-card p-4 text-center transition hover:border-primary hover:bg-accent"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-lg font-semibold text-primary">
                  {member.name.charAt(0).toUpperCase()}
                </div>
                <span className="font-medium">{member.name}</span>
                <span className="text-xs capitalize text-muted-foreground">{member.role}</span>
              </button>
            ))}
            {staff.length === 0 && (
              <p className="col-span-full text-sm text-muted-foreground">No staff found for this location.</p>
            )}
          </div>
        )}
        <Button variant="ghost" className="mt-6 text-xs" onClick={() => router.push('/setup')}>
          Change location
        </Button>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-muted/40 p-4">
      <Card className="w-full max-w-xs">
        <CardHeader className="items-center text-center">
          <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Lock className="h-6 w-6 text-primary" />
          </div>
          <CardTitle>{selected.name}</CardTitle>
          <p className="text-sm capitalize text-muted-foreground">{selected.role}</p>
        </CardHeader>
        <CardContent className="flex flex-col items-center gap-4">
          <div className="flex gap-3">
            {Array.from({ length: PIN_LENGTH }).map((_, i) => (
              <div
                key={i}
                className={`h-3 w-3 rounded-full border ${
                  i < pin.length ? 'border-primary bg-primary' : 'border-muted-foreground/40'
                }`}
              />
            ))}
          </div>
          <div className="grid grid-cols-3 gap-2">
            {['1', '2', '3', '4', '5', '6', '7', '8', '9'].map((d) => (
              <Button
                key={d}
                type="button"
                variant="outline"
                className="h-14 w-14 text-lg"
                disabled={submitting}
                onClick={() => handleDigit(d)}
              >
                {d}
              </Button>
            ))}
            <Button
              type="button"
              variant="ghost"
              className="h-14 w-14"
              disabled={submitting}
              onClick={() => {
                setSelected(null)
                setPin('')
              }}
            >
              Back
            </Button>
            <Button
              type="button"
              variant="outline"
              className="h-14 w-14 text-lg"
              disabled={submitting}
              onClick={() => handleDigit('0')}
            >
              0
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="h-14 w-14"
              disabled={submitting}
              onClick={() => setPin((p) => p.slice(0, -1))}
            >
              <Delete className="h-5 w-5" />
            </Button>
          </div>
          {submitting && <Spinner />}
        </CardContent>
      </Card>
    </div>
  )
}
