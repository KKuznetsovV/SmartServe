'use client'

import { useMutation } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import type { AiCommandRequest } from '@smartserve/types'

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
