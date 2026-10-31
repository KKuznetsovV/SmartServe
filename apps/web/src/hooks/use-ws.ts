'use client'

import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { WsEvent } from '@smartserve/types'
import { apiClient } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'

export function nextWsReconnectDelay(attempt: number): number {
  return Math.min(1000 * 2 ** Math.max(attempt, 0), 15000)
}

function orderIdFromPayload(payload: WsEvent['payload']): string | undefined {
  const id = payload?.id ?? payload?.orderId
  return typeof id === 'string' ? id : undefined
}

function invalidateOrders(qc: ReturnType<typeof useQueryClient>, locationId: string) {
  qc.invalidateQueries({ queryKey: ['orders', locationId] })
  qc.invalidateQueries({ queryKey: ['order'] })
}

// Connects to the location WebSocket and invalidates order queries on events.
export function useLocationWs(locationId: string | null) {
  const qc = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)
  const accessToken = useAuthStore((s) => s.accessToken)

  useEffect(() => {
    if (!locationId || !accessToken) return

    const base = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8080').replace(
      /^http/,
      'ws',
    )
    let disposed = false
    let attempt = 0
    let timer: ReturnType<typeof setTimeout> | undefined
    let everOpened = false

    const connect = () => {
      if (disposed) return
      void (async () => {
        let ticket: string
        try {
          const issued = await apiClient.ws.ticket(locationId)
          ticket = issued.ticket
        } catch {
          if (disposed) return
          const delay = nextWsReconnectDelay(attempt)
          attempt += 1
          timer = setTimeout(connect, delay)
          return
        }
        if (disposed) return
        const ws = new WebSocket(
          `${base}/api/v1/ws/${locationId}?ticket=${encodeURIComponent(ticket)}`,
        )
        wsRef.current = ws

        ws.onopen = () => {
          if (disposed) return
          if (everOpened) {
            invalidateOrders(qc, locationId)
          }
          everOpened = true
          attempt = 0
        }

        ws.onmessage = (event) => {
          try {
            const msg: WsEvent = JSON.parse(event.data as string)
            if (msg.type.startsWith('order.')) {
              qc.invalidateQueries({ queryKey: ['orders', locationId] })
              const id = orderIdFromPayload(msg.payload)
              if (typeof id === 'string') qc.invalidateQueries({ queryKey: ['order', id] })
            }
            if (msg.type === 'menu.item_updated') {
              qc.invalidateQueries({ queryKey: ['items'] })
              qc.invalidateQueries({ queryKey: ['categories', locationId] })
            }
          } catch {
            // ignore malformed messages
          }
        }

        ws.onclose = () => {
          if (disposed) return
          const delay = nextWsReconnectDelay(attempt)
          attempt += 1
          timer = setTimeout(connect, delay)
        }
      })()
    }

    connect()

    return () => {
      disposed = true
      if (timer) clearTimeout(timer)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [locationId, accessToken, qc])
}
