'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiClient } from '@/lib/api'
import type { Printer, PrinterRoute } from '@smartserve/types'

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
  return useMutation({
    mutationFn: (data: Omit<Printer, 'id'>) => apiClient.printers.create(data),
    onSuccess: (p) => {
      qc.invalidateQueries({ queryKey: ['printers', p.locationId] })
      toast.success('Printer added')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUpdatePrinter() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, locationId, data }: { id: string; locationId: string; data: Partial<Printer> }) =>
      apiClient.printers.update(id, data),
    onSuccess: (_, { locationId }) => {
      qc.invalidateQueries({ queryKey: ['printers', locationId] })
      toast.success('Printer updated')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useDeletePrinter() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id }: { id: string; locationId: string }) => apiClient.printers.delete(id),
    onSuccess: (_, { locationId }) => {
      qc.invalidateQueries({ queryKey: ['printers', locationId] })
      toast.success('Printer removed')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useSetPrinterRoute() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ route }: { route: PrinterRoute; locationId: string }) =>
      apiClient.printers.setRoute(route),
    onSuccess: (_, { locationId }) => {
      qc.invalidateQueries({ queryKey: ['printer-routes', locationId] })
    },
    onError: (e: Error) => toast.error(e.message),
  })
}
