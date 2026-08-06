'use client'

import { useEffect } from 'react'
import { useAuthStore } from '@/lib/auth-store'
import { apiClient } from '@/lib/api'
import { getJwtExpiryMs } from '@/lib/jwt'

// Refresh a bit before actual expiry so the browser never has to log a failed
// 401 request against a live session (React Query's window-focus refetch was
// tripping this after the access token's 15min lifetime elapsed on an idle tab).
const REFRESH_BUFFER_MS = 60_000

export function useTokenRefresh() {
  const accessToken = useAuthStore((s) => s.accessToken)
  const refreshToken = useAuthStore((s) => s.refreshToken)
  const setTokens = useAuthStore((s) => s.setTokens)
  const clearAuth = useAuthStore((s) => s.clearAuth)

  useEffect(() => {
    if (!accessToken || !refreshToken) return

    const expiryMs = getJwtExpiryMs(accessToken)
    if (!expiryMs) return
    const delay = Math.max(expiryMs - Date.now() - REFRESH_BUFFER_MS, 0)

    const timer = setTimeout(async () => {
      try {
        const tokens = await apiClient.auth.refresh(refreshToken)
        setTokens(tokens.accessToken, tokens.refreshToken)
      } catch {
        clearAuth()
      }
    }, delay)

    return () => clearTimeout(timer)
  }, [accessToken, refreshToken, setTokens, clearAuth])
}
