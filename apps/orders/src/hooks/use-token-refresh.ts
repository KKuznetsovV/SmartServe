'use client'

import { useEffect } from 'react'
import { useAuthStore } from '@/lib/auth-store'
import { apiClient } from '@/lib/api'
import { getJwtExpiryMs } from '@/lib/jwt'

const REFRESH_BUFFER_MS = 60_000

export function useTokenRefresh() {
  const accessToken = useAuthStore((s) => s.accessToken)
  const setTokens = useAuthStore((s) => s.setTokens)
  const clearAuth = useAuthStore((s) => s.clearAuth)

  useEffect(() => {
    if (!accessToken) return

    const expiryMs = getJwtExpiryMs(accessToken)
    if (!expiryMs) return
    const remaining = expiryMs - Date.now()
    const buffer = Math.min(REFRESH_BUFFER_MS, Math.max(remaining * 0.2, 0))
    const delay = Math.max(remaining - buffer, 0)

    const timer = setTimeout(async () => {
      try {
        const tokens = await apiClient.auth.refresh()
        setTokens(tokens.accessToken)
      } catch {
        clearAuth()
      }
    }, delay)

    return () => clearTimeout(timer)
  }, [accessToken, setTokens, clearAuth])
}
