'use client'

import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import type { AiChange, AiCommandResponse } from '@smartserve/types'

const LOW_CONFIDENCE = 0.85

export type ConfirmationEntryStatus = 'pending' | 'confirmed' | 'dismissed' | 'error'

interface AiConfirmationCardProps {
  response: AiCommandResponse
  status: ConfirmationEntryStatus
  resultMessage?: string
  isLoading: boolean
  onConfirm: () => void
  onDismiss: () => void
}

function formatValue(change: AiChange, value: unknown, t: ReturnType<typeof useTranslations<'ai'>>): string {
  if (change.field === 'inStock') {
    return value ? t('inStockTrue') : t('inStockFalse')
  }
  if (change.field === 'create' && value && typeof value === 'object') {
    const body = value as { name?: string; price?: number }
    if (body.price != null) return `${body.name ?? change.name} (${body.price})`
    return body.name ?? change.name
  }
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? t('inStockTrue') : t('inStockFalse')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

/** Proposed-action confirmation card for the AI assistant chat — the assistant never
 * executes a change (price update, delete, low-confidence intent) until the manager
 * explicitly confirms it here. */
export function AiConfirmationCard({
  response,
  status,
  resultMessage,
  isLoading,
  onConfirm,
  onDismiss,
}: AiConfirmationCardProps) {
  const t = useTranslations('ai')
  const intentKey = `intent_${response.intent}`
  const label = t.has(intentKey) ? t(intentKey) : t('proposedAction')
  const changes = response.changes ?? []
  const summary = response.summary || response.preview
  const unsupported = response.supported === false
  const showConfirm = status === 'pending' && response.requiresConfirmation && !unsupported && Boolean(response.executionId)

  return (
    <Card
      className={
        status === 'confirmed'
          ? 'border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/40'
          : status === 'error' || unsupported
            ? 'border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950/40'
            : ''
      }
    >
      <CardContent className="p-4 space-y-3">
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{label}</p>
          <p className="text-sm" dir="auto">
            {unsupported ? response.message || summary : summary}
          </p>
          {response.confidence < LOW_CONFIDENCE && !unsupported && (
            <p className="text-xs text-amber-600 dark:text-amber-400">{t('lowConfidence')}</p>
          )}
        </div>

        {response.scope === 'location' && (
          <div className="rounded-md border border-red-300 bg-red-100 px-3 py-2 text-xs text-red-800 dark:border-red-800 dark:bg-red-950/60 dark:text-red-200">
            {t('locationScopeWarning')}
          </div>
        )}

        {changes.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">{t('changeCount', { count: changes.length })}</p>
            <div className="overflow-x-auto rounded-md border">
              <table className="w-full text-xs">
                <thead className="bg-muted/50 text-muted-foreground">
                  <tr>
                    <th className="px-2 py-1 text-start font-medium">{t('changeItem')}</th>
                    <th className="px-2 py-1 text-start font-medium">{t('changeFrom')}</th>
                    <th className="px-2 py-1 text-start font-medium">{t('changeTo')}</th>
                  </tr>
                </thead>
                <tbody>
                  {changes.map((change, index) => (
                    <tr key={`${change.id ?? change.name}-${change.field}-${index}`} className="border-t">
                      <td className="px-2 py-1">{change.name}</td>
                      <td className="px-2 py-1 font-mono">{formatValue(change, change.from, t)}</td>
                      <td className="px-2 py-1 font-mono">{formatValue(change, change.to, t)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {status === 'confirmed' && <p className="text-xs text-green-700 dark:text-green-400 font-medium">✓ {resultMessage}</p>}
        {status === 'error' && <p className="text-xs text-red-600 dark:text-red-400">{resultMessage}</p>}

        {showConfirm && (
          <div className="flex gap-2">
            <Button size="sm" onClick={onConfirm} disabled={isLoading}>
              {t('confirmButton')}
            </Button>
            <Button size="sm" variant="outline" onClick={onDismiss}>
              {t('dismiss')}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
