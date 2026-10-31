import type { WsTicket } from '@smartserve/types'

import type { Http } from './client'

export function createWsResource(http: Http) {
  return {
    ticket: (locationId: string) => http.post<WsTicket>('/ws/ticket', { locationId }),
  }
}
