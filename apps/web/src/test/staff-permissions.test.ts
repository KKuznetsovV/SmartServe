import { describe, expect, it } from 'vitest'
import { assignableRoles } from '@smartserve/types'

describe('assignableRoles', () => {
  it('lets an owner assign every role including owner', () => {
    expect(assignableRoles('owner')).toEqual(['owner', 'manager', 'cashier', 'waiter', 'kitchen'])
  })

  it('lets a manager assign only strictly lower roles', () => {
    expect(assignableRoles('manager')).toEqual(['cashier', 'waiter', 'kitchen'])
  })
})
