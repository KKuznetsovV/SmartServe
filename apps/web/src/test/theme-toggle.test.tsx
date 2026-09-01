import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent } from '@testing-library/react'
import { renderHook, act } from '@testing-library/react'
import { ThemeToggle, useThemeToggle } from '@smartserve/ui'

function mockMatchMedia(initialMatches: boolean) {
  let matches = initialMatches
  const listeners: Array<() => void> = []
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    get matches() {
      return matches
    },
    media: query,
    addEventListener: (_: string, listener: () => void) => listeners.push(listener),
    removeEventListener: () => {},
  })) as unknown as typeof window.matchMedia
  return {
    setMatches: (next: boolean) => {
      matches = next
      listeners.forEach((l) => l())
    },
  }
}

describe('ThemeToggle (presentational)', () => {
  afterEach(cleanup)

  it('marks the active preference as pressed', () => {
    render(<ThemeToggle theme="dark" onChange={() => {}} labels={{ light: 'Light', dark: 'Dark', system: 'System' }} />)
    expect(screen.getByRole('button', { name: 'Dark' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: 'Light' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('calls onChange with the clicked preference', () => {
    const onChange = vi.fn()
    render(<ThemeToggle theme="light" onChange={onChange} labels={{ light: 'Light', dark: 'Dark', system: 'System' }} />)
    fireEvent.click(screen.getByRole('button', { name: 'Dark' }))
    expect(onChange).toHaveBeenCalledWith('dark')
  })

  it('does not call onChange when clicking the already-active preference', () => {
    const onChange = vi.fn()
    render(<ThemeToggle theme="system" onChange={onChange} labels={{ light: 'Light', dark: 'Dark', system: 'System' }} />)
    fireEvent.click(screen.getByRole('button', { name: 'System' }))
    expect(onChange).not.toHaveBeenCalled()
  })
})

describe('useThemeToggle (applies + persists resolved theme)', () => {
  beforeEach(() => {
    document.cookie = 'theme=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/'
    document.documentElement.classList.remove('dark')
  })
  afterEach(cleanup)

  it('applies the dark class when the preference is explicitly dark', () => {
    mockMatchMedia(false)
    const { result } = renderHook(() => useThemeToggle(() => {}))
    act(() => result.current.setTheme('dark'))
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('removes the dark class when the preference is explicitly light', () => {
    mockMatchMedia(true)
    const { result } = renderHook(() => useThemeToggle(() => {}))
    act(() => result.current.setTheme('light'))
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('resolves "system" against the OS color-scheme preference', () => {
    mockMatchMedia(true)
    const { result } = renderHook(() => useThemeToggle(() => {}))
    act(() => result.current.setTheme('system'))
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('calls the persist callback with the newly selected preference', () => {
    mockMatchMedia(false)
    const onPersist = vi.fn()
    const { result } = renderHook(() => useThemeToggle(onPersist))
    act(() => result.current.setTheme('dark'))
    expect(onPersist).toHaveBeenCalledWith('dark')
  })

  it('re-resolves the dark class when the OS preference changes while set to system', () => {
    const { setMatches } = mockMatchMedia(false)
    const { result } = renderHook(() => useThemeToggle(() => {}))
    act(() => result.current.setTheme('system'))
    expect(document.documentElement.classList.contains('dark')).toBe(false)

    // Simulate the OS switching to dark mode while "system" stays selected.
    act(() => setMatches(true))
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })
})
