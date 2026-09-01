'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useTranslations } from 'next-intl'
import { apiClient } from '@/lib/api'
import type { Order, OrderItem } from '@smartserve/types'

export function useOrders(locationId: string | null, status?: string) {
  return useQuery({
    queryKey: ['orders', locationId, status ?? 'all'],
    queryFn: () => apiClient.orders.list(locationId!, status),
    enabled: !!locationId,
    refetchInterval: 10_000, // poll every 10s as fallback behind WS
  })
}

export function useOrder(orderId: string | null) {
  return useQuery({
    queryKey: ['order', orderId],
    queryFn: () => apiClient.orders.get(orderId!),
    enabled: !!orderId,
  })
}

export function useCreateOrder() {
  const qc = useQueryClient()
  const t = useTranslations('orders')
  return useMutation({
    mutationFn: (data: Pick<Order, 'locationId' | 'tableId' | 'channel'>) =>
      apiClient.orders.create(data),
    onSuccess: (o) => {
      qc.invalidateQueries({ queryKey: ['orders', o.locationId] })
      toast.success(t('toastCreated'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useAddOrderItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      orderId,
      item,
    }: {
      orderId: string
      locationId: string
      item: Omit<OrderItem, 'id' | 'orderId' | 'status'>
    }) => apiClient.orders.addItem(orderId, item),
    onSuccess: (_, { orderId, locationId }) => {
      qc.invalidateQueries({ queryKey: ['order', orderId] })
      qc.invalidateQueries({ queryKey: ['orders', locationId] })
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useSubmitOrder() {
  const qc = useQueryClient()
  const t = useTranslations('orders')
  return useMutation({
    mutationFn: ({ orderId }: { orderId: string; locationId: string }) =>
      apiClient.orders.submit(orderId),
    onSuccess: (o) => {
      qc.invalidateQueries({ queryKey: ['order', o.id] })
      qc.invalidateQueries({ queryKey: ['orders', o.locationId] })
      toast.success(t('toastSubmitted'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUpdateOrderItemStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, itemId, status }: { orderId: string; itemId: string; status: string }) =>
      apiClient.orders.updateItemStatus(orderId, itemId, status),
    onSuccess: (item) => {
      qc.invalidateQueries({ queryKey: ['order', item.orderId] })
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useCancelOrder() {
  const qc = useQueryClient()
  const t = useTranslations('orders')
  return useMutation({
    mutationFn: ({ orderId }: { orderId: string; locationId: string }) =>
      apiClient.orders.cancel(orderId),
    onSuccess: (o) => {
      qc.invalidateQueries({ queryKey: ['order', o.id] })
      qc.invalidateQueries({ queryKey: ['orders', o.locationId] })
      toast.success(t('toastCancelled'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}
