import '@testing-library/jest-dom'

// jsdom doesn't implement ResizeObserver, which recharts' ResponsiveContainer
// needs — stub it so chart-rendering components don't throw in tests.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
;(globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver = ResizeObserverStub
