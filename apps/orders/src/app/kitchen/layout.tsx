import { Suspense, type ReactNode } from 'react'
import { AuthReadyGate } from '@/components/auth-ready-gate'
import { Spinner } from '@/components/ui/spinner'

// Full-screen dark layout for kitchen display — no sidebar
export default function KitchenLayout({ children }: { children: ReactNode }) {
  return (
    <AuthReadyGate>
      <div className="min-h-screen bg-zinc-950 text-zinc-100">
        <Suspense
          fallback={
            <div className="flex justify-center py-12">
              <Spinner />
            </div>
          }
        >
          {children}
        </Suspense>
      </div>
    </AuthReadyGate>
  )
}
