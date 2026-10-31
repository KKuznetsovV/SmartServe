import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest'
import { renderHook, waitFor, cleanup, act } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { nextWsReconnectDelay, useLocationWs } from '@/hooks/use-ws'
import { useAuthStore } from '@/lib/auth-store'
import { apiClient } from '@/lib/api'
import type { ReactNode } from 'react'

vi.mock('@/lib/api', () => ({
  apiClient: {
    ws: {
      ticket: vi.fn(),
    },
  },
}))

class MockWebSocket {
  static instances: MockWebSocket[] = []
  onmessage: ((event: MessageEvent) => void) | null = null
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  url: string
  readyState = 0

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
    queueMicrotask(() => {
      this.readyState = 1
      this.onopen?.(new Event('open'))
    })
  }

  close() {
    this.readyState = 3
    this.onclose?.(new CloseEvent('close'))
  }

  emit(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent)
  }
}

function wrapperFor(qc: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

describe('useLocationWs', () => {
  beforeEach(() => {
    let n = 0
    vi.mocked(apiClient.ws.ticket).mockImplementation(async () => ({
      ticket: `ticket-${++n}`,
      expiresIn: 60,
    }))
    useAuthStore.setState({ accessToken: 'jwt-token' })
  })

  afterEach(() => {
    cleanup()
    MockWebSocket.instances = []
    vi.unstubAllGlobals()
    vi.useRealTimers()
    useAuthStore.setState({ accessToken: null })
  })

  it('invalidates order list and detail using payload.orderId', async () => {
    vi.stubGlobal('WebSocket', MockWebSocket)
    const qc = new QueryClient()
    const invalidate = vi.spyOn(qc, 'invalidateQueries')
    const locationId = '11111111-1111-1111-1111-111111111111'
    const orderId = '22222222-2222-2222-2222-222222222222'

    renderHook(() => useLocationWs(locationId), { wrapper: wrapperFor(qc) })

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1))
    expect(MockWebSocket.instances[0].url).toContain('ticket=ticket-1')
    MockWebSocket.instances[0].emit({
      type: 'order.item_status_changed',
      locationId,
      payload: { orderId, status: 'preparing' },
      timestamp: new Date().toISOString(),
    })

    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['orders', locationId] })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['order', orderId] })
  })

  it('reconnects with backoff, fetches a new ticket, and invalidates orders after a drop', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('WebSocket', MockWebSocket)
    const qc = new QueryClient()
    const invalidate = vi.spyOn(qc, 'invalidateQueries')
    const locationId = '11111111-1111-1111-1111-111111111111'

    renderHook(() => useLocationWs(locationId), { wrapper: wrapperFor(qc) })
    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })
    expect(MockWebSocket.instances).toHaveLength(1)

    act(() => {
      MockWebSocket.instances[0].close()
    })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
      await Promise.resolve()
      await Promise.resolve()
    })
    expect(MockWebSocket.instances).toHaveLength(2)
    expect(MockWebSocket.instances[1].url).toContain('ticket=ticket-2')
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['orders', locationId] })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['order'] })
  })

  it('caps reconnect delay at 15s', () => {
    expect(nextWsReconnectDelay(0)).toBe(1000)
    expect(nextWsReconnectDelay(1)).toBe(2000)
    expect(nextWsReconnectDelay(2)).toBe(4000)
    expect(nextWsReconnectDelay(10)).toBe(15000)
  })
})
