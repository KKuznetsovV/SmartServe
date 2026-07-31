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
