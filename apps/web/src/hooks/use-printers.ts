'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useTranslations } from 'next-intl'
import { apiClient } from '@/lib/api'
import type { Printer } from '@smartserve/types'

export function usePrinters(locationId: string | null) {
  return useQuery({
    queryKey: ['printers', locationId],
    queryFn: () => apiClient.printers.list(locationId!),
    enabled: !!locationId,
  })
}

export function usePrinterRoutes(locationId: string | null) {
  return useQuery({
    queryKey: ['printer-routes', locationId],
    queryFn: () => apiClient.printers.listRoutes(locationId!),
    enabled: !!locationId,
  })
}

export function useCreatePrinter() {
  const qc = useQueryClient()
  const t = useTranslations('printers')
  return useMutation({
    mutationFn: (data: Omit<Printer, 'id'>) => apiClient.printers.create(data),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ['printers', p.locationId] })
      toast.success(t('toastAdded'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUpdatePrinter() {
  const qc = useQueryClient()
  const t = useTranslations('printers')
  return useMutation({
    mutationFn: ({ id, locationId, data }: { id: string; locationId: string; data: Partial<Printer> }) =>
      apiClient.printers.update(id, data),
    onSuccess: (_, { locationId }) => {
      qc.invalidateQueries({ queryKey: ['printers', locationId] })
      toast.success(t('toastUpdated'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useDeletePrinter() {
  const qc = useQueryClient()
  const t = useTranslations('printers')
  return useMutation({
    mutationFn: ({ id }: { id: string; locationId: string }) => apiClient.printers.delete(id),
    onSuccess: (_, { locationId }) => {
      qc.invalidateQueries({ queryKey: ['printers', locationId] })
      toast.success(t('toastRemoved'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useAddPrinterRoute() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ printerId, itemId }: { printerId: string; itemId: string; locationId: string }) =>
      apiClient.printers.addRoute(printerId, itemId),
    onSuccess: (_, { locationId }) => {
      qc.invalidateQueries({ queryKey: ['printer-routes', locationId] })
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useDeletePrinterRoute() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ routeId }: { routeId: string; locationId: string }) =>
      apiClient.printers.deleteRoute(routeId),
    onSuccess: (_, { locationId }) => {
      qc.invalidateQueries({ queryKey: ['printer-routes', locationId] })
    },
    onError: (e: Error) => toast.error(e.message),
  })
}
