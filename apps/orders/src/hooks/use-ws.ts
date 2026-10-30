'use client'

import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { WsEvent } from '@smartserve/types'

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

  useEffect(() => {
    if (!locationId) return

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
      const ws = new WebSocket(`${base}/api/v1/ws/${locationId}`)
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
            if (id) qc.invalidateQueries({ queryKey: ['order', id] })
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
    }

    connect()

    return () => {
      disposed = true
      if (timer) clearTimeout(timer)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [locationId, qc])
}
