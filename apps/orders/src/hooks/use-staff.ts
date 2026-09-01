'use client'

import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'

/** Staff list for the current business — used to resolve/filter orders by the server who created them.
 * Only owners/managers are authorized to list staff, so callers should gate `enabled` on the current
 * user's role and treat a disabled/errored query as "server names unavailable". */
export function useStaff(businessId: string | null, enabled = true) {
  return useQuery({
    queryKey: ['staff', businessId],
    queryFn: () => apiClient.staff.list(businessId!),
    enabled: !!businessId && enabled,
  })
}
