'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useTranslations } from 'next-intl'
import { apiClient } from '@/lib/api'
import type { ItemSelection } from '@smartserve/api-client'
import type { Order, OrderItem, OrderItemModifierInput } from '@smartserve/types'

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
    mutationFn: (data: Pick<Order, 'locationId' | 'tableId' | 'channel'> & Partial<Pick<Order, 'guestCount'>>) =>
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
      item: Omit<
        OrderItem,
        'id' | 'orderId' | 'status' | 'sortOrder' | 'fireCourse' | 'discountAmount' | 'isComped' | 'modifiers'
      > &
        Partial<Pick<OrderItem, 'fireCourse'>> & { modifiers?: OrderItemModifierInput[] }
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
      qc.invalidateQueries({ queryKey: ['orders'] })
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUpdateOrderItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      orderId,
      itemId,
      data,
    }: {
      orderId: string
      itemId: string
      data: Partial<Pick<OrderItem, 'qty' | 'notes' | 'fireCourse'>> & {
        modifiers?: OrderItemModifierInput[]
      }
    }) => apiClient.orders.updateItem(orderId, itemId, data),
    onSuccess: (item) => {
      qc.invalidateQueries({ queryKey: ['order', item.orderId] })
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useReorderOrderItems() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, ids }: { orderId: string; ids: string[] }) => apiClient.orders.reorderItems(orderId, ids),
    onMutate: async ({ orderId, ids }) => {
      await qc.cancelQueries({ queryKey: ['order', orderId] })
      const previous = qc.getQueryData<Order>(['order', orderId])
      if (previous) {
        const byId = new Map(previous.items.map((i) => [i.id, i]))
        qc.setQueryData<Order>(['order', orderId], {
          ...previous,
          items: ids.map((id, index) => ({ ...byId.get(id)!, sortOrder: index })),
        })
      }
      return { previous }
    },
    onError: (e: Error, { orderId }, context) => {
      if (context?.previous) qc.setQueryData(['order', orderId], context.previous)
      toast.error(e.message)
    },
    onSettled: (_, __, { orderId }) => {
      qc.invalidateQueries({ queryKey: ['order', orderId] })
    },
  })
}

export function useRemoveOrderItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, itemId }: { orderId: string; itemId: string }) =>
      apiClient.orders.removeItem(orderId, itemId),
    onMutate: async ({ orderId, itemId }) => {
      await qc.cancelQueries({ queryKey: ['order', orderId] })
      const previous = qc.getQueryData<Order>(['order', orderId])
      if (previous) {
        qc.setQueryData<Order>(['order', orderId], {
          ...previous,
          items: previous.items.filter((i) => i.id !== itemId),
        })
      }
      return { previous }
    },
    onError: (e: Error, { orderId }, context) => {
      if (context?.previous) qc.setQueryData(['order', orderId], context.previous)
      toast.error(e.message)
    },
    onSettled: (_, __, { orderId }) => {
      qc.invalidateQueries({ queryKey: ['order', orderId] })
    },
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

export function useFireCourse() {
  const qc = useQueryClient()
  const t = useTranslations('orders')
  return useMutation({
    mutationFn: ({ orderId, course }: { orderId: string; course: number }) =>
      apiClient.orders.fireCourse(orderId, course),
    onSuccess: (o) => {
      qc.invalidateQueries({ queryKey: ['order', o.id] })
      qc.invalidateQueries({ queryKey: ['orders', o.locationId] })
      toast.success(t('toastCourseFired'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useAssignGuests() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      orderId,
      assignments,
    }: {
      orderId: string
      assignments: (ItemSelection & { guestNumber: number | null })[]
    }) => apiClient.orders.assignGuests(orderId, assignments),
    onSuccess: (o) => {
      qc.invalidateQueries({ queryKey: ['order', o.id] })
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useApplyItemDiscount() {
  const qc = useQueryClient()
  const t = useTranslations('orders')
  return useMutation({
    mutationFn: ({
      orderId,
      items,
      discountType,
      discountValue,
    }: {
      orderId: string
      items: ItemSelection[]
      discountType: 'percent' | 'fixed' | null
      discountValue: number | null
    }) => apiClient.orders.applyItemDiscount(orderId, items, discountType, discountValue),
    onSuccess: (o) => {
      qc.invalidateQueries({ queryKey: ['order', o.id] })
      toast.success(t('toastDiscountApplied'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useSetItemComp() {
  const qc = useQueryClient()
  const t = useTranslations('orders')
  return useMutation({
    mutationFn: ({ orderId, items, comped }: { orderId: string; items: ItemSelection[]; comped: boolean }) =>
      apiClient.orders.setItemComp(orderId, items, comped),
    onSuccess: (o, { comped }) => {
      qc.invalidateQueries({ queryKey: ['order', o.id] })
      toast.success(comped ? t('toastComped') : t('toastCompRemoved'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useDeleteOrderItems() {
  const qc = useQueryClient()
  const t = useTranslations('orders')
  return useMutation({
    mutationFn: ({
      orderId,
      items,
      override,
    }: {
      orderId: string
      items: ItemSelection[]
      override?: { managerUserId: string; pin: string; reason: string }
    }) => apiClient.orders.deleteItems(orderId, items, override),
    onSuccess: (o) => {
      qc.invalidateQueries({ queryKey: ['order', o.id] })
      toast.success(t('toastItemDeleted'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}
