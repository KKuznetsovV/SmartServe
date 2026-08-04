'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@smartserve/types'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  activeBusinessId: string | null
  activeLocationId: string | null
  setAuth: (accessToken: string, refreshToken: string, user: User) => void
  setTokens: (accessToken: string, refreshToken: string) => void
  setActiveLocation: (businessId: string, locationId: string) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      activeBusinessId: null,
      activeLocationId: null,
      setAuth: (accessToken, refreshToken, user) =>
        set({ accessToken, refreshToken, user }),
      setTokens: (accessToken, refreshToken) =>
        set({ accessToken, refreshToken }),
      setActiveLocation: (activeBusinessId, activeLocationId) =>
        set({ activeBusinessId, activeLocationId }),
      clearAuth: () =>
        set({
          accessToken: null,
          refreshToken: null,
          user: null,
          activeBusinessId: null,
          activeLocationId: null,
        }),
    }),
    { name: 'smartserve-auth' },
  ),
)
