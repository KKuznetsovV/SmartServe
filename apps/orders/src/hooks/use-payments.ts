'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useTranslations } from 'next-intl'
import { apiClient } from '@/lib/api'
import type { Payment } from '@smartserve/types'

export function useOrderPayments(orderId: string | null) {
  return useQuery({
    queryKey: ['payments', orderId],
    queryFn: () => apiClient.payments.listByOrder(orderId!),
    enabled: !!orderId,
  })
}

export function useCreatePayment() {
  const qc = useQueryClient()
  const t = useTranslations('payments')
  return useMutation({
    mutationFn: (
      data: Pick<Payment, 'orderId' | 'method' | 'amount'> & Partial<Pick<Payment, 'tipAmount' | 'guestNumber'>>,
    ) => apiClient.payments.create(data),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ['payments', p.orderId] })
      qc.invalidateQueries({ queryKey: ['orders'] })
      if (p.orderFullyPaid) {
        qc.setQueryData(['order', p.orderId], (current: { status: string } | undefined) =>
          current ? { ...current, status: 'paid' } : current,
        )
      }
      toast.success(t('toastRecorded'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}
