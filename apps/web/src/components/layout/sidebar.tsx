'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  UtensilsCrossed,
  Users,
  Printer,
  BarChart3,
  Settings,
  Sparkles,
  LogOut,
  ChefHat,
  Tag,
  Package,
  Clock,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAuthStore } from '@/lib/auth-store'
import { useTranslations } from 'next-intl'
import { LocaleToggle } from './locale-toggle'

const navItems = [
  { href: '/dashboard', icon: LayoutDashboard, key: 'dashboard' },
  { href: '/menu', icon: UtensilsCrossed, key: 'menu', managerOnly: true },
  { href: '/staff', icon: Users, key: 'staff', managerOnly: true },
  { href: '/printers', icon: Printer, key: 'printers', managerOnly: true },
  { href: '/reports', icon: BarChart3, key: 'reports' },
  { href: '/ai', icon: Sparkles, key: 'ai' },
  { href: '/stock', icon: Package, key: 'stock' },
  { href: '/shifts', icon: Clock, key: 'shifts' },
  { href: '/settings/discounts', icon: Tag, key: 'discounts', managerOnly: true },
  { href: '/settings', icon: Settings, key: 'settings' },
]

export function Sidebar() {
  const pathname = usePathname()
  const { user, clearAuth } = useAuthStore()
  const isManager = user?.role === 'owner' || user?.role === 'manager'
  const tNav = useTranslations('nav')
  const tAuth = useTranslations('auth')

  return (
    <aside className="flex h-screen w-60 flex-col border-r bg-card">
      {/* Logo */}
      <div className="flex h-14 items-center justify-between gap-2 border-b px-4">
        <div className="flex items-center gap-2">
          <ChefHat className="h-6 w-6 text-primary" />
          <span className="font-bold text-lg">SmartServe</span>
        </div>
        <LocaleToggle />
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-4">
        {navItems
          .filter((item) => !item.managerOnly || isManager)
          .map(({ href, icon: Icon, key }) => (
            <Link
              key={key}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-md mx-2 px-3 py-2 text-sm font-medium transition-colors',
                pathname.startsWith(href) && href !== '/dashboard'
                  ? 'bg-primary text-primary-foreground'
                  : pathname === href
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-foreground',
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {tNav(key as Parameters<typeof tNav>[0])}
            </Link>
          ))}
      </nav>

      {/* User */}
      <div className="border-t p-4">
        <div className="mb-2 text-sm font-medium truncate">{user?.name ?? user?.email}</div>
        <button
          onClick={clearAuth}
          className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <LogOut className="h-4 w-4" />
          <span>{tAuth('logout')}</span>
        </button>
      </div>
    </aside>
  )
}
