import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent } from '@testing-library/react'
import { LanguageSwitcher } from '@smartserve/ui'

describe('LanguageSwitcher (presentational)', () => {
  afterEach(cleanup)

  it('shows the current locale', () => {
    render(<LanguageSwitcher locale="he" onChange={() => {}} />)
    expect(screen.getByRole('button', { name: 'Language: HE' }).textContent).toBe('HE')
  })

  it('toggles from Hebrew to English on click', () => {
    const onChange = vi.fn()
    render(<LanguageSwitcher locale="he" onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: 'Language: HE' }))
    expect(onChange).toHaveBeenCalledWith('en')
  })

  it('toggles from English to Hebrew on click', () => {
    const onChange = vi.fn()
    render(<LanguageSwitcher locale="en" onChange={onChange} />)
    fireEvent.click(screen.getByRole('button', { name: 'Language: EN' }))
    expect(onChange).toHaveBeenCalledWith('he')
  })
})
