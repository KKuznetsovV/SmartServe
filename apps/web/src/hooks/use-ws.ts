'use client'

import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { WsEvent } from '@smartserve/types'

// Connects to the location WebSocket and invalidates order queries on events.
export function useLocationWs(locationId: string | null) {
  const qc = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!locationId) return

    const base = (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000').replace(
      /^http/,
      'ws',
    )
    const ws = new WebSocket(`${base}/api/v1/ws/${locationId}`)
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const msg: WsEvent = JSON.parse(event.data as string)
        if (msg.type.startsWith('order.')) {
          qc.invalidateQueries({ queryKey: ['orders', locationId] })
          const id = msg.payload?.id as string | undefined
          if (id) qc.invalidateQueries({ queryKey: ['order', id] })
        }
      } catch {
        // ignore malformed messages
      }
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [locationId, qc])
}
