'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useTranslations } from 'next-intl'
import { apiClient } from '@/lib/api'

export function useCurrentShift(locationId: string | null) {
  return useQuery({
    queryKey: ['shift-current', locationId],
    queryFn: () => apiClient.shifts.current(locationId!),
    enabled: !!locationId,
    staleTime: 30_000,
  })
}

export function useShiftHistory(locationId: string | null) {
  return useQuery({
    queryKey: ['shifts', locationId],
    queryFn: () => apiClient.shifts.list(locationId!),
    enabled: !!locationId,
  })
}

export function useOpenShift() {
  const qc = useQueryClient()
  const t = useTranslations('shifts')
  return useMutation({
    mutationFn: ({ locationId, openingCash, notes }: { locationId: string; openingCash: number; notes?: string }) =>
      apiClient.shifts.open(locationId, openingCash, notes),
    onSuccess: (shift) => {
      qc.invalidateQueries({ queryKey: ['shift-current', shift.locationId] })
      qc.invalidateQueries({ queryKey: ['shifts', shift.locationId] })
      toast.success(t('toastOpened'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useCloseShift() {
  const qc = useQueryClient()
  const t = useTranslations('shifts')
  return useMutation({
    mutationFn: ({ shiftId, locationId, closingCash, notes }: { shiftId: string; locationId: string; closingCash: number; notes?: string }) =>
      apiClient.shifts.close(shiftId, closingCash, notes),
    onSuccess: (shift) => {
      qc.invalidateQueries({ queryKey: ['shift-current', shift.locationId] })
      qc.invalidateQueries({ queryKey: ['shifts', shift.locationId] })
      toast.success(t('toastClosed'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}
