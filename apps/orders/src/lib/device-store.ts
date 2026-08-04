'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface DeviceState {
  /** The location this device/browser is configured for (set once by a manager). */
  locationId: string | null
  setLocationId: (locationId: string) => void
  clearLocationId: () => void
}

export const useDeviceStore = create<DeviceState>()(
  persist(
    (set) => ({
      locationId: null,
      setLocationId: (locationId) => set({ locationId }),
      clearLocationId: () => set({ locationId: null }),
    }),
    { name: 'smartserve-device' },
  ),
)
