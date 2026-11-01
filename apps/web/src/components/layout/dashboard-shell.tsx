'use client'

import { useState } from 'react'
import { Menu, X } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { Sidebar } from './sidebar'

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const tNav = useTranslations('nav')

  return (
    <div className="flex h-screen overflow-hidden">
      <div className="hidden h-full lg:block">
        <Sidebar />
      </div>

      {open && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true">
          <button
            type="button"
            className="absolute inset-0 bg-black/40"
            aria-label={tNav('closeMenu')}
            onClick={() => setOpen(false)}
          />
          <div className="relative z-10 h-full w-60 bg-card shadow-xl">
            <div className="absolute inset-inline-end-2 top-2 z-20">
              <button
                type="button"
                className="flex min-h-12 min-w-12 items-center justify-center rounded-md hover:bg-accent"
                aria-label={tNav('closeMenu')}
                onClick={() => setOpen(false)}
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <Sidebar testId="admin-sidebar-drawer" onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center gap-2 border-b bg-card px-3 lg:hidden">
          <button
            type="button"
            data-testid="open-admin-menu"
            className="flex min-h-12 min-w-12 items-center justify-center rounded-md hover:bg-accent"
            aria-label={tNav('openMenu')}
            onClick={() => setOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="whitespace-nowrap text-lg font-bold">SmartServe</span>
        </header>
        <main className="min-w-0 flex-1 overflow-y-auto overflow-x-hidden">{children}</main>
      </div>
    </div>
  )
}
