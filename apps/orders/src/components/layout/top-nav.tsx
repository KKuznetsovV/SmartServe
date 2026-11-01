'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChefHat, ClipboardList, Grid3x3, LogOut, Menu, Monitor, X } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/lib/auth-store'
import { signOut } from '@/lib/auth-session'
import { LocaleToggle } from './locale-toggle'
import { ThemeToggle } from './theme-toggle'

const navItems = [
  { href: '/orders', icon: ClipboardList, key: 'orders' },
  { href: '/tables', icon: Grid3x3, key: 'tables' },
]

export function TopNav() {
  const pathname = usePathname()
  const { user } = useAuthStore()
  const tNav = useTranslations('nav')
  const tAuth = useTranslations('auth')
  const [menuOpen, setMenuOpen] = useState(false)

  const extraLinks = (
    <>
      <a
        href="/kitchen"
        target="_blank"
        rel="noopener noreferrer"
        className="flex min-h-12 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      >
        <ChefHat className="h-4 w-4 shrink-0" />
        {tNav('kitchenDisplay')}
      </a>
      <a
        href="/display"
        target="_blank"
        rel="noopener noreferrer"
        className="flex min-h-12 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      >
        <Monitor className="h-4 w-4 shrink-0" />
        {tNav('customerDisplay')}
      </a>
      <button
        onClick={() => void signOut()}
        className="flex min-h-12 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
      >
        <LogOut className="h-4 w-4" />
        <span>{tAuth('logout')}</span>
      </button>
    </>
  )

  return (
    <header className="relative flex h-14 items-center gap-2 border-b bg-card px-3 sm:px-4">
      <div className="flex shrink-0 items-center gap-2 pe-2 sm:pe-4">
        <ChefHat className="h-6 w-6 shrink-0 text-primary" />
        <span className="whitespace-nowrap text-lg font-bold">SmartServe</span>
      </div>

      <nav className="flex min-w-0 flex-1 items-center gap-1">
        {navItems.map(({ href, icon: Icon, key }) => (
          <Link
            key={key}
            href={href}
            className={cn(
              'flex min-h-12 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              pathname.startsWith(href)
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-accent hover:text-foreground',
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {tNav(key as Parameters<typeof tNav>[0])}
          </Link>
        ))}
        <div className="hidden items-center gap-1 lg:flex">{extraLinks}</div>
      </nav>

      <div className="hidden items-center gap-3 lg:flex">
        <LocaleToggle />
        <ThemeToggle />
        <span className="max-w-32 truncate text-sm font-medium">{user?.name}</span>
      </div>

      <button
        type="button"
        data-testid="open-orders-menu"
        className="ms-auto flex min-h-12 min-w-12 items-center justify-center rounded-md hover:bg-accent lg:hidden"
        aria-label={menuOpen ? tNav('closeMenu') : tNav('openMenu')}
        onClick={() => setMenuOpen((v) => !v)}
      >
        {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {menuOpen && (
        <div
          data-testid="orders-overflow-menu"
          className="absolute inset-inline-end-2 top-14 z-50 flex w-56 flex-col rounded-md border bg-card p-2 shadow-lg lg:hidden"
        >
          <div className="mb-2 flex items-center gap-2 px-2">
            <LocaleToggle />
            <ThemeToggle />
          </div>
          {extraLinks}
        </div>
      )}
    </header>
  )
}
