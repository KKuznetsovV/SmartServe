'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ChefHat } from 'lucide-react'
import { toast } from 'sonner'
import { useTranslations } from 'next-intl'
import { safeInternalPath } from '@smartserve/ui'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'
import { apiClient } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { useAuthReady } from '@/hooks/use-auth-ready'
import { LocaleToggle } from '@/components/layout/locale-toggle'
import { ThemeToggle } from '@/components/layout/theme-toggle'

const schema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(1, 'Password is required'),
})
type FormData = z.infer<typeof schema>

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
  const t = useTranslations('auth')
  const router = useRouter()
  const searchParams = useSearchParams()
  const { ready, authenticated } = useAuthReady()
  const setAuth = useAuthStore((s) => s.setAuth)
  const setTokens = useAuthStore((s) => s.setTokens)
  const setActiveLocation = useAuthStore((s) => s.setActiveLocation)
  const [loading, setLoading] = useState(false)
  const afterLogin = safeInternalPath(searchParams.get('next'), '/menu')

  useEffect(() => {
    if (ready && authenticated) {
      router.replace(afterLogin)
    }
  }, [ready, authenticated, afterLogin, router])

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: FormData) => {
    setLoading(true)
    try {
      const tokens = await apiClient.auth.login(data.email, data.password)
      // Store tokens first so the /auth/me request carries the Authorization header
      setTokens(tokens.accessToken, tokens.refreshToken)
      const user = await apiClient.auth.me()
      setAuth(tokens.accessToken, tokens.refreshToken, user)

      // Fetch first available location for this business
      if (user.businessId) {
        const locations = await apiClient.locations.list(user.businessId)
        if (locations.length > 0) {
          setActiveLocation(user.businessId, locations[0].id)
        }
      }

      router.push(afterLogin)
    } catch (e) {
      toast.error((e as Error).message ?? t('invalidCredentials'))
    } finally {
      setLoading(false)
    }
  }

  if (!ready || authenticated) {
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
            <ChefHat className="h-6 w-6 text-primary" />
          </div>
          <CardTitle className="text-2xl">SmartServe</CardTitle>
          <p className="text-sm text-muted-foreground">{t('managerPortal')}</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1">
              <Label htmlFor="email">{t('email')}</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="manager@restaurant.com"
                {...register('email')}
              />
              {errors.email && (
                <p className="text-xs text-destructive">{errors.email.message}</p>
              )}
            </div>
            <div className="space-y-1">
              <Label htmlFor="password">{t('password')}</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register('password')}
              />
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? <Spinner className="me-2" /> : null}
              {t('loginButton')}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
