'use client'

import { useEffect, useRef } from 'react'
import { Delete } from 'lucide-react'
import { Button } from '@/components/ui/button'

const DIGITS = ['1', '2', '3', '4', '5', '6', '7', '8', '9'] as const

interface PinPadProps {
  pinLength: number
  pin: string
  disabled?: boolean
  backLabel: string
  deleteLabel: string
  onDigit: (digit: string) => void
  onBackspace: () => void
  onBack: () => void
  onEnter?: () => void
}

/** Numeric keypad forced LTR so Hebrew `dir=rtl` on `<html>` does not reverse 1–9 or swap Back/Delete. */
export function PinPad({
  pinLength,
  pin,
  disabled,
  backLabel,
  deleteLabel,
  onDigit,
  onBackspace,
  onBack,
  onEnter,
}: PinPadProps) {
  const onDigitRef = useRef(onDigit)
  const onBackspaceRef = useRef(onBackspace)
  const onEnterRef = useRef(onEnter)
  const disabledRef = useRef(disabled)
  onDigitRef.current = onDigit
  onBackspaceRef.current = onBackspace
  onEnterRef.current = onEnter
  disabledRef.current = disabled

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (disabledRef.current) return
      if (event.key >= '0' && event.key <= '9') {
        event.preventDefault()
        onDigitRef.current(event.key)
        return
      }
      if (event.key === 'Backspace') {
        event.preventDefault()
        onBackspaceRef.current()
        return
      }
      if (event.key === 'Enter') {
        event.preventDefault()
        onEnterRef.current?.()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="flex gap-3" aria-hidden="true">
        {Array.from({ length: pinLength }).map((_, i) => (
          <div
            key={i}
            className={`h-3 w-3 rounded-full border ${
              i < pin.length ? 'border-primary bg-primary' : 'border-muted-foreground/40'
            }`}
          />
        ))}
      </div>
      <div
        dir="ltr"
        data-testid="pin-pad"
        className="grid grid-cols-3 gap-2"
        role="group"
        aria-label="PIN keypad"
      >
        {DIGITS.map((d) => (
          <Button
            key={d}
            type="button"
            variant="outline"
            className="h-14 min-h-12 w-14 min-w-12 text-lg"
            disabled={disabled}
            onClick={() => onDigit(d)}
          >
            {d}
          </Button>
        ))}
        <Button
          type="button"
          variant="ghost"
          className="h-14 min-h-12 w-14 min-w-12"
          disabled={disabled}
          onClick={onBack}
          data-testid="pin-pad-back"
        >
          {backLabel}
        </Button>
        <Button
          type="button"
          variant="outline"
          className="h-14 min-h-12 w-14 min-w-12 text-lg"
          disabled={disabled}
          onClick={() => onDigit('0')}
        >
          0
        </Button>
        <Button
          type="button"
          variant="ghost"
          className="h-14 min-h-12 w-14 min-w-12"
          disabled={disabled}
          aria-label={deleteLabel}
          onClick={onBackspace}
          data-testid="pin-pad-delete"
        >
          <Delete className="h-5 w-5" aria-hidden="true" />
        </Button>
      </div>
    </div>
  )
}
