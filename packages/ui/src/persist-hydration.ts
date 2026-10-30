'use client'

import { useEffect, useState } from 'react'

/**
 * Minimal persist API used by Zustand's persist middleware.
 * Typed structurally so `@smartserve/ui` does not depend on zustand.
 */
export interface PersistHydrationApi {
  persist: {
    hasHydrated: () => boolean
    onFinishHydration: (fn: () => void) => () => void
  }
}

/**
 * True after `store.persist` has finished rehydrating (or immediately if it
 * already has). Always starts false so SSR and the first client paint match.
 */
export function useHasHydrated(store: PersistHydrationApi): boolean {
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    const finish = () => setHydrated(true)
    const unsubscribe = store.persist.onFinishHydration(finish)
    if (store.persist.hasHydrated()) finish()
    return unsubscribe
  }, [store])

  return hydrated
}
