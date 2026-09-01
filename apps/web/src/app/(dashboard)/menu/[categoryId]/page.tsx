'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Plus } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { useMenuItems } from '@/hooks/use-menu'
import { ItemCard } from '@/components/menu/item-card'
import { ItemFormDialog } from '@/components/menu/item-form-dialog'
import type { MenuItem } from '@smartserve/types'

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function CategoryItemsPage() {
  const t = useTranslations('menu')
  const params = useParams()
  const router = useRouter()
  const categoryId = params.categoryId as string

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<MenuItem | null>(null)

  const { data: items = [], isLoading } = useMenuItems(categoryId)

  const openCreate = () => {
    setEditing(null)
    setDialogOpen(true)
  }

  const openEdit = (item: MenuItem) => {
    setEditing(item)
    setDialogOpen(true)
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.push('/menu')}>
          <ArrowLeft className="h-5 w-5 rtl:-scale-x-100" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{t('itemsTitle')}</h1>
          <p className="text-sm text-muted-foreground">
            {t('itemsCount', { count: items.length })}
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="me-1 h-4 w-4" />
          {t('addItem')}
        </Button>
      </div>

      {/* Items */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
          <p className="mb-4 text-muted-foreground">{t('noItemsInCategory')}</p>
          <Button variant="outline" onClick={openCreate}>
            <Plus className="me-1 h-4 w-4" />
            {t('addFirstItem')}
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 items-start gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {items.map((item) => (
            <ItemCard key={item.id} item={item} categoryId={categoryId} onEdit={openEdit} />
          ))}
        </div>
      )}

      <ItemFormDialog open={dialogOpen} onOpenChange={setDialogOpen} categoryId={categoryId} editing={editing} />
    </div>
  )
}
