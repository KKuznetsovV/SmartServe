'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { useTranslations } from 'next-intl'
import { apiClient } from '@/lib/api'
import type { Table } from '@smartserve/types'

export function useTables(locationId: string | null, includeStatus = false) {
  return useQuery({
    queryKey: ['tables', locationId, includeStatus ? 'status' : 'basic'],
    queryFn: () => apiClient.tables.list(locationId!, includeStatus ? 'status' : undefined),
    enabled: !!locationId,
  })
}

export function useCreateTable() {
  const qc = useQueryClient()
  const t = useTranslations('tables')
  return useMutation({
    mutationFn: (data: Omit<Table, 'id'>) => apiClient.tables.create(data),
    onSuccess: (tbl) => {
      qc.invalidateQueries({ queryKey: ['tables', tbl.locationId] })
      toast.success(t('toastCreated'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUpdateTable() {
  const qc = useQueryClient()
  const t = useTranslations('tables')
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Table> }) =>
      apiClient.tables.update(id, data),
    onSuccess: (tbl) => {
      qc.invalidateQueries({ queryKey: ['tables', tbl.locationId] })
      toast.success(t('toastUpdated'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useDeleteTable() {
  const qc = useQueryClient()
  const t = useTranslations('tables')
  return useMutation({
    mutationFn: ({ id, locationId }: { id: string; locationId: string }) =>
      apiClient.tables.delete(id),
    onSuccess: (_, { locationId }) => {
      qc.invalidateQueries({ queryKey: ['tables', locationId] })
      toast.success(t('toastDeleted'))
    },
    onError: (e: Error) => toast.error(e.message),
  })
}
