'use client'

import { TopNav } from '@/components/layout/top-nav'
import { AuthReadyGate } from '@/components/auth-ready-gate'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthReadyGate>
      <div className="flex h-screen flex-col overflow-hidden">
        <TopNav />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </AuthReadyGate>
  )
}
