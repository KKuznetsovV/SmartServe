'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiClient } from '@/lib/api'
import type { Table } from '@smartserve/types'

export function useTables(locationId: string | null) {
  return useQuery({
    queryKey: ['tables', locationId],
    queryFn: () => apiClient.tables.list(locationId!),
    enabled: !!locationId,
  })
}

export function useCreateTable() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Omit<Table, 'id'>) => apiClient.tables.create(data),
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ['tables', t.locationId] })
      toast.success('Table created')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUpdateTable() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Table> }) =>
      apiClient.tables.update(id, data),
    onSuccess: (t) => {
      qc.invalidateQueries({ queryKey: ['tables', t.locationId] })
      toast.success('Table updated')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useDeleteTable() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, locationId }: { id: string; locationId: string }) =>
      apiClient.tables.delete(id),
    onSuccess: (_, { locationId }) => {
      qc.invalidateQueries({ queryKey: ['tables', locationId] })
      toast.success('Table deleted')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}
