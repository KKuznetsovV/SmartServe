import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge } from '@/components/ui/badge'

describe('Badge', () => {
  it('renders its text content', () => {
    render(<Badge>Active</Badge>)
    expect(screen.getByText('Active')).toBeInTheDocument()
  })

  it('applies success variant', () => {
    render(<Badge variant="success">Paid</Badge>)
    expect(screen.getByText('Paid').className).toContain('bg-emerald-100')
  })

  it('applies warning variant', () => {
    render(<Badge variant="warning">Pending</Badge>)
    expect(screen.getByText('Pending').className).toContain('bg-amber-100')
  })

  it('applies destructive variant', () => {
    render(<Badge variant="destructive">Void</Badge>)
    expect(screen.getByText('Void').className).toContain('bg-destructive')
  })

  it('merges extra className', () => {
    render(<Badge className="ms-2">Tag</Badge>)
    expect(screen.getByText('Tag').className).toContain('ms-2')
  })
})
