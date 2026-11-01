import { describe, it, expect, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PinPad } from '@/components/pin-pad'

describe('PinPad', () => {
  it('keeps 1-2-3 order and Back left of Delete inside an RTL container', async () => {
    const onDigit = vi.fn()
    const onBackspace = vi.fn()
    const onBack = vi.fn()
    render(
      <div dir="rtl">
        <PinPad
          pinLength={4}
          pin=""
          backLabel="חזור"
          deleteLabel="מחק ספרה אחרונה"
          onDigit={onDigit}
          onBackspace={onBackspace}
          onBack={onBack}
        />
      </div>,
    )

    const pad = screen.getByTestId('pin-pad')
    expect(pad).toHaveAttribute('dir', 'ltr')

    const buttons = within(pad).getAllByRole('button')
    expect(buttons.map((b) => b.textContent?.trim())).toEqual([
      '1',
      '2',
      '3',
      '4',
      '5',
      '6',
      '7',
      '8',
      '9',
      'חזור',
      '0',
      '',
    ])
    expect(buttons[0]).toHaveAccessibleName('1')
    expect(buttons[2]).toHaveAccessibleName('3')
    expect(buttons[9]).toHaveAccessibleName('חזור')
    expect(buttons[11]).toHaveAccessibleName('מחק ספרה אחרונה')

    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: '1' }))
    await user.click(screen.getByRole('button', { name: 'מחק ספרה אחרונה' }))
    expect(onDigit).toHaveBeenCalledWith('1')
    expect(onBackspace).toHaveBeenCalledTimes(1)
  })

  it('accepts digits, Backspace and Enter from the keyboard', async () => {
    const onDigit = vi.fn()
    const onBackspace = vi.fn()
    const onEnter = vi.fn()
    const user = userEvent.setup()
    render(
      <PinPad
        pinLength={4}
        pin=""
        backLabel="Back"
        deleteLabel="Delete last digit"
        onDigit={onDigit}
        onBackspace={onBackspace}
        onBack={vi.fn()}
        onEnter={onEnter}
      />,
    )
    await user.keyboard('12{Backspace}34{Enter}')
    expect(onDigit.mock.calls.map((c) => c[0])).toEqual(['1', '2', '3', '4'])
    expect(onBackspace).toHaveBeenCalledTimes(1)
    expect(onEnter).toHaveBeenCalledTimes(1)
  })
})
