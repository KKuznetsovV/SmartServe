'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChefHat, ClipboardList, Grid3x3, LogOut, Monitor } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/lib/auth-store'
import { LocaleToggle } from './locale-toggle'
import { ThemeToggle } from './theme-toggle'

const navItems = [
  { href: '/orders', icon: ClipboardList, key: 'orders' },
  { href: '/tables', icon: Grid3x3, key: 'tables' },
]

export function TopNav() {
  const pathname = usePathname()
  const { user, clearAuth } = useAuthStore()
  const tNav = useTranslations('nav')
  const tAuth = useTranslations('auth')

  return (
    <header className="flex h-14 items-center gap-2 border-b bg-card px-4">
      <div className="flex items-center gap-2 pe-4">
        <ChefHat className="h-6 w-6 text-primary" />
        <span className="text-lg font-bold">SmartServe</span>
      </div>

      <nav className="flex flex-1 items-center gap-1">
        {navItems.map(({ href, icon: Icon, key }) => (
          <Link
            key={key}
            href={href}
            className={cn(
              'flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              pathname.startsWith(href)
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-accent hover:text-foreground',
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            {tNav(key as Parameters<typeof tNav>[0])}
          </Link>
        ))}
        <a
          href="/kitchen"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <ChefHat className="h-4 w-4 shrink-0" />
          {tNav('kitchenDisplay')}
        </a>
        <a
          href="/display"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <Monitor className="h-4 w-4 shrink-0" />
          {tNav('customerDisplay')}
        </a>
      </nav>

      <div className="flex items-center gap-3">
        <LocaleToggle />
        <ThemeToggle />
        <span className="truncate text-sm font-medium">{user?.name}</span>
        <button
          onClick={clearAuth}
          className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <LogOut className="h-4 w-4" />
          <span>{tAuth('logout')}</span>
        </button>
      </div>
    </header>
  )
}
