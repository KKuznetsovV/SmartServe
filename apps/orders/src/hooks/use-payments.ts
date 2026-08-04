'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
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
  return useMutation({
    mutationFn: (data: Pick<Payment, 'orderId' | 'method' | 'amount'>) =>
      apiClient.payments.create(data),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ['payments', p.orderId] })
      qc.invalidateQueries({ queryKey: ['order', p.orderId] })
      qc.invalidateQueries({ queryKey: ['orders'] })
      toast.success('Payment recorded')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}
