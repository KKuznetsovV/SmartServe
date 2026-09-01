'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useTranslations } from 'next-intl'
import { apiClient } from '@/lib/api'

export function useLocationStock(locationId: string | null) {
  return useQuery({
    queryKey: ['stock', locationId],
    queryFn: () => apiClient.menuItems.listStock(locationId!),
    enabled: !!locationId,
    staleTime: 15_000,
  })
}

export function useSetStock() {
  const qc = useQueryClient()
  const t = useTranslations('stock')
  return useMutation({
    mutationFn: ({ id, inStock }: { id: string; locationId: string; inStock: boolean }) =>
      apiClient.menuItems.setStock(id, inStock),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['stock', vars.locationId] })
      toast.success(vars.inStock ? t('toastMarkedIn') : t('toastMarkedOut'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}
