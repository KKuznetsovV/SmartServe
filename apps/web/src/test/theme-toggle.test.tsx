import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent } from '@testing-library/react'
import { renderHook, act } from '@testing-library/react'
import { ThemeToggle, useThemeToggle } from '@smartserve/ui'

describe('ThemeToggle (presentational)', () => {
  afterEach(cleanup)

  it('marks dark mode as pressed', () => {
    render(<ThemeToggle theme="dark" onChange={() => {}} labels={{ light: 'Light', dark: 'Dark' }} />)
    expect(screen.getByRole('button', { name: 'Theme: Dark' }).getAttribute('aria-pressed')).toBe('true')
  })

  it('toggles from light to dark on click', () => {
    const onChange = vi.fn()
    render(<ThemeToggle theme="light" onChange={onChange} labels={{ light: 'Light', dark: 'Dark' }} />)
    fireEvent.click(screen.getByRole('button', { name: 'Theme: Light' }))
    expect(onChange).toHaveBeenCalledWith('dark')
  })

  it('toggles from dark to light on click', () => {
    const onChange = vi.fn()
    render(<ThemeToggle theme="dark" onChange={onChange} labels={{ light: 'Light', dark: 'Dark' }} />)
    fireEvent.click(screen.getByRole('button', { name: 'Theme: Dark' }))
    expect(onChange).toHaveBeenCalledWith('light')
  })
})

describe('useThemeToggle (applies + persists resolved theme)', () => {
  beforeEach(() => {
    document.cookie = 'theme=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/'
    document.documentElement.classList.remove('dark')
  })
  afterEach(cleanup)

  it('applies the dark class when the preference is explicitly dark', () => {
    const { result } = renderHook(() => useThemeToggle(() => {}))
    act(() => result.current.setTheme('dark'))
    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })

  it('removes the dark class when the preference is explicitly light', () => {
    const { result } = renderHook(() => useThemeToggle(() => {}))
    act(() => result.current.setTheme('light'))
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('calls the persist callback with the newly selected preference', () => {
    const onPersist = vi.fn()
    const { result } = renderHook(() => useThemeToggle(onPersist))
    act(() => result.current.setTheme('dark'))
    expect(onPersist).toHaveBeenCalledWith('dark')
  })
})
