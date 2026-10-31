'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '@smartserve/types'

interface AuthState {
  accessToken: string | null
  user: User | null
  activeBusinessId: string | null
  activeLocationId: string | null
  setAuth: (accessToken: string, user: User) => void
  setTokens: (accessToken: string) => void
  setActiveLocation: (businessId: string, locationId: string) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      user: null,
      activeBusinessId: null,
      activeLocationId: null,
      setAuth: (accessToken, user) => set({ accessToken, user }),
      setTokens: (accessToken) => set({ accessToken }),
      setActiveLocation: (activeBusinessId, activeLocationId) =>
        set({ activeBusinessId, activeLocationId }),
      clearAuth: () =>
        set({
          accessToken: null,
          user: null,
          activeBusinessId: null,
          activeLocationId: null,
        }),
    }),
    {
      name: 'smartserve-auth',
      partialize: (state) => ({
        activeBusinessId: state.activeBusinessId,
        activeLocationId: state.activeLocationId,
      }),
      merge: (persisted, current) => ({
        ...current,
        ...(persisted as object),
        accessToken: null,
      }),
    },
  ),
)
