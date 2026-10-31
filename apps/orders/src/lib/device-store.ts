'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { DeviceType } from '@smartserve/types'

interface DeviceState {
  locationId: string | null
  deviceToken: string | null
  deviceType: DeviceType | null
  deviceName: string | null
  setDevice: (input: {
    locationId: string
    deviceToken: string
    deviceType: DeviceType
    deviceName: string
  }) => void
  clearDevice: () => void
}

export const useDeviceStore = create<DeviceState>()(
  persist(
    (set) => ({
      locationId: null,
      deviceToken: null,
      deviceType: null,
      deviceName: null,
      setDevice: (input) => set(input),
      clearDevice: () =>
        set({ locationId: null, deviceToken: null, deviceType: null, deviceName: null }),
    }),
    { name: 'smartserve-device' },
  ),
)
