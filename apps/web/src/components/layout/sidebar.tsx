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
import { signOut } from '@/lib/auth-session'
import { useTranslations } from 'next-intl'
import { LocaleToggle } from './locale-toggle'
import { ThemeToggle } from './theme-toggle'

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

export function Sidebar({
  onNavigate,
  testId = 'admin-sidebar',
}: {
  onNavigate?: () => void
  testId?: string
}) {
  const pathname = usePathname()
  const { user } = useAuthStore()
  const isManager = user?.role === 'owner' || user?.role === 'manager'
  const tNav = useTranslations('nav')
  const tAuth = useTranslations('auth')

  return (
    <aside
      data-testid={testId}
      className="flex h-full w-60 shrink-0 flex-col overflow-hidden border-e bg-card"
    >
      <div className="flex h-14 min-w-0 items-center justify-between gap-2 border-b px-3">
        <div className="flex min-w-0 items-center gap-2">
          <ChefHat className="h-6 w-6 shrink-0 text-primary" />
          <span className="whitespace-nowrap font-bold text-lg">SmartServe</span>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <LocaleToggle />
          <ThemeToggle />
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-4">
        {navItems
          .filter((item) => !item.managerOnly || isManager)
          .map(({ href, icon: Icon, key }) => (
            <Link
              key={key}
              href={href}
              onClick={onNavigate}
              className={cn(
                'mx-2 flex min-h-12 items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
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

      <div className="border-t p-4">
        <div className="mb-2 truncate text-sm font-medium">{user?.name ?? user?.email}</div>
        <button
          onClick={() => void signOut()}
          className="flex min-h-12 w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <LogOut className="h-4 w-4" />
          <span>{tAuth('logout')}</span>
        </button>
      </div>
    </aside>
  )
}
