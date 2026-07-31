'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiClient } from '@/lib/api'
import type { User } from '@smartserve/types'

export function useStaff(businessId: string | null) {
  return useQuery({
    queryKey: ['staff', businessId],
    queryFn: () => apiClient.staff.list(businessId!),
    enabled: !!businessId,
  })
}

export function useCreateStaff() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Omit<User, 'id'> & { password?: string; pin?: string }) =>
      apiClient.staff.create(data),
    onSuccess: (u) => {
      qc.invalidateQueries({ queryKey: ['staff', u.businessId] })
      toast.success('Staff member added')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUpdateStaff() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; businessId: string; data: Partial<User> & { pin?: string } }) =>
      apiClient.staff.update(id, data),
    onSuccess: (u) => {
      qc.invalidateQueries({ queryKey: ['staff', u.businessId] })
      toast.success('Staff member updated')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}
