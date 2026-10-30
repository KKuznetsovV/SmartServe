import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { safeInternalPath, useHasHydrated, withLoginNext } from '@smartserve/ui'

describe('safeInternalPath', () => {
  it('falls back when missing or external', () => {
    expect(safeInternalPath(null, '/menu')).toBe('/menu')
    expect(safeInternalPath('https://evil.test', '/menu')).toBe('/menu')
    expect(safeInternalPath('//evil.test', '/menu')).toBe('/menu')
    expect(safeInternalPath('reports', '/menu')).toBe('/menu')
  })

  it('keeps same-origin paths including query strings', () => {
    expect(safeInternalPath('/staff', '/menu')).toBe('/staff')
    expect(safeInternalPath('/reports?tab=sales', '/menu')).toBe('/reports?tab=sales')
  })
})

describe('withLoginNext', () => {
  it('encodes the destination on /login', () => {
    expect(withLoginNext('/login', '/staff')).toBe('/login?next=%2Fstaff')
  })
})

describe('useHasHydrated', () => {
  it('stays false until persist finishes, then flips true', () => {
    const listeners: Array<() => void> = []
    let hydrated = false
    const store = {
      persist: {
        hasHydrated: () => hydrated,
        onFinishHydration: (fn: () => void) => {
          listeners.push(fn)
          return () => {
            const i = listeners.indexOf(fn)
            if (i >= 0) listeners.splice(i, 1)
          }
        },
      },
    }

    const { result } = renderHook(() => useHasHydrated(store))
    expect(result.current).toBe(false)

    act(() => {
      hydrated = true
      listeners.forEach((fn) => fn())
    })
    expect(result.current).toBe(true)
  })

  it('is true immediately when persist has already hydrated', () => {
    const store = {
      persist: {
        hasHydrated: () => true,
        onFinishHydration: (fn: () => void) => {
          fn()
          return () => {}
        },
      },
    }
    const { result } = renderHook(() => useHasHydrated(store))
    expect(result.current).toBe(true)
  })
})
