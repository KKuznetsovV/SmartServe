'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import type { AiCommandRequest, MenuImportItem } from '@smartserve/types'

export function useAiCommand() {
  return useMutation({
    mutationFn: (data: AiCommandRequest) => apiClient.ai.command(data),
  })
}

export function useAiConfirm() {
  return useMutation({
    mutationFn: (executionId: string) => apiClient.ai.confirm(executionId),
  })
}

export function useMenuImportUpload() {
  return useMutation({
    mutationFn: ({ locationId, file }: { locationId: string; file: File }) =>
      apiClient.ai.importMenuFile(locationId, file),
  })
}

export function useMenuImportMessage() {
  return useMutation({
    mutationFn: ({ sessionId, message }: { sessionId: string; message: string }) =>
      apiClient.ai.importMenuMessage(sessionId, message),
  })
}

export function useMenuImportApply() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      sessionId,
      items,
    }: {
      sessionId: string
      items?: MenuImportItem[]
      locationId: string
    }) => apiClient.ai.importMenuApply(sessionId, items),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ['categories', variables.locationId] })
      qc.invalidateQueries({ queryKey: ['items'] })
      qc.invalidateQueries({ queryKey: ['printer-routes', variables.locationId] })
    },
  })
}
