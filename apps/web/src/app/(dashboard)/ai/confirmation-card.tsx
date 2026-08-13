'use client'

import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import type { AiCommandResponse } from '@smartserve/types'

export const INTENT_LABELS: Record<string, string> = {
  'menu.create_item': 'Create menu item',
  'menu.update_item': 'Update menu item',
  'menu.bulk_price_change': 'Bulk price change',
  'menu.toggle_availability': 'Toggle availability',
  'menu.create_category': 'Create category',
  'menu.create_modifier_group': 'Create modifier group',
  'printer.route': 'Configure print routing',
  'printer.troubleshoot': 'Printer troubleshoot',
  'report.query': 'Report query',
  'staff.add_user': 'Add staff member',
  'staff.set_permissions': 'Set permissions',
  'inventory.set_threshold': 'Inventory threshold',
  'settings.business': 'Business settings',
  'help.general': 'Help',
}

export function confidenceColor(c: number) {
  if (c >= 0.85) return 'text-green-600'
  if (c >= 0.6) return 'text-amber-600'
  return 'text-red-500'
}

export type ConfirmationEntryStatus = 'pending' | 'confirmed' | 'dismissed' | 'error'

interface AiConfirmationCardProps {
  response: AiCommandResponse
  status: ConfirmationEntryStatus
  resultMessage?: string
  isLoading: boolean
  onConfirm: () => void
  onDismiss: () => void
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
  return (
    <Card
      className={
        status === 'confirmed'
          ? 'border-green-200 bg-green-50'
          : status === 'error'
            ? 'border-red-200 bg-red-50'
            : ''
      }
    >
      <CardContent className="p-4 space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {INTENT_LABELS[response.intent] ?? response.intent}
            </p>
            {/* dir="auto" so a Hebrew preview renders RTL even when the dashboard's own
             * locale/dir is set to English (and vice versa) */}
            <p className="text-sm" dir="auto">
              {response.preview}
            </p>
          </div>
          <span className={`text-xs font-mono whitespace-nowrap ${confidenceColor(response.confidence)}`}>
            {Math.round(response.confidence * 100)}%
          </span>
        </div>

        {status === 'confirmed' && <p className="text-xs text-green-700 font-medium">✓ {resultMessage}</p>}
        {status === 'error' && <p className="text-xs text-red-600">{resultMessage}</p>}

        {status === 'pending' && response.requiresConfirmation && (
          <div className="flex gap-2">
            <Button size="sm" onClick={onConfirm} disabled={isLoading}>
              Confirm
            </Button>
            <Button size="sm" variant="outline" onClick={onDismiss}>
              Dismiss
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
