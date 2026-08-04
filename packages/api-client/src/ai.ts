import type { AiCommandRequest, AiCommandResponse, MenuImportItem, MenuImportTurn, MenuImportApplyResponse } from '@smartserve/types'

import type { Http } from './client'

export function createAiResource(http: Http) {
  return {
    command: (data: AiCommandRequest) => http.post<AiCommandResponse>('/ai/command', data),
    confirm: (executionId: string) =>
      http.post<{ success: boolean; message: string }>('/ai/confirm', { executionId }),
    importMenuFile: (locationId: string, file: File) => {
      const form = new FormData()
      form.append('location_id', locationId)
      form.append('file', file)
      return http.postForm<MenuImportTurn>('/ai/menu-import', form)
    },
    importMenuMessage: (sessionId: string, message: string) =>
      http.post<MenuImportTurn>('/ai/menu-import/message', { sessionId, message }),
    importMenuApply: (sessionId: string, items?: MenuImportItem[]) =>
      http.post<MenuImportApplyResponse>('/ai/menu-import/apply', { sessionId, items }),
  }
}
