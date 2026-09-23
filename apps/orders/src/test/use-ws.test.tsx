import { describe, it, expect, vi, afterEach } from 'vitest'
import { renderHook, waitFor, cleanup } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useLocationWs } from '@/hooks/use-ws'
import type { ReactNode } from 'react'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  onmessage: ((event: MessageEvent) => void) | null = null
  url: string
  readyState = 1

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  close() {
    this.readyState = 3
  }

  emit(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent)
  }
}

describe('useLocationWs', () => {
  afterEach(() => {
    cleanup()
    MockWebSocket.instances = []
    vi.unstubAllGlobals()
  })

  it('invalidates order list and detail using payload.orderId', async () => {
    vi.stubGlobal('WebSocket', MockWebSocket)
    const qc = new QueryClient()
    const invalidate = vi.spyOn(qc, 'invalidateQueries')
    const locationId = '11111111-1111-1111-1111-111111111111'
    const orderId = '22222222-2222-2222-2222-222222222222'

    function Wrapper({ children }: { children: ReactNode }) {
      return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    }

    renderHook(() => useLocationWs(locationId), { wrapper: Wrapper })

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1))
    MockWebSocket.instances[0].emit({
      type: 'order.item_status_changed',
      locationId,
      payload: { orderId, status: 'preparing' },
      timestamp: new Date().toISOString(),
    })

    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['orders', locationId] })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['order', orderId] })
  })
})
