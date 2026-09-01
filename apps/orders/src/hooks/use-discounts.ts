'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useTranslations } from 'next-intl'
import { apiClient } from '@/lib/api'
import type { Discount } from '@smartserve/types'

export function useDiscounts(businessId: string | null) {
  return useQuery({
    queryKey: ['discounts', businessId],
    queryFn: () => apiClient.discounts.list(businessId!),
    enabled: !!businessId,
    staleTime: 30_000,
  })
}

export function useCreateDiscount() {
  const qc = useQueryClient()
  const t = useTranslations('discounts')
  return useMutation({
    mutationFn: (data: Omit<Discount, 'id' | 'createdAt'>) => apiClient.discounts.create(data),
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ['discounts', d.businessId] })
      toast.success(t('toastCreated'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUpdateDiscount() {
  const qc = useQueryClient()
  const t = useTranslations('discounts')
  return useMutation({
    mutationFn: ({
      id,
      businessId,
      data,
    }: {
      id: string
      businessId: string
      data: Partial<Pick<Discount, 'name' | 'value' | 'minOrderAmount' | 'active' | 'expiresAt'>>
    }) => apiClient.discounts.update(id, data),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['discounts', vars.businessId] })
      toast.success(t('toastUpdated'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useDeleteDiscount() {
  const qc = useQueryClient()
  const t = useTranslations('discounts')
  return useMutation({
    mutationFn: ({ id }: { id: string; businessId: string }) => apiClient.discounts.delete(id),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['discounts', vars.businessId] })
      toast.success(t('toastDeleted'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useApplyDiscount() {
  const qc = useQueryClient()
  const t = useTranslations('discounts')
  return useMutation({
    mutationFn: ({ orderId, code }: { orderId: string; code: string }) =>
      apiClient.orders.applyDiscount(orderId, code),
    onSuccess: (order) => {
      qc.invalidateQueries({ queryKey: ['order', order.id] })
      qc.invalidateQueries({ queryKey: ['orders'] })
      toast.success(t('toastApplied'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}
