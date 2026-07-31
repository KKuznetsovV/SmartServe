'use client'

import { useState, useRef, useEffect } from 'react'
import { useAiCommand, useAiConfirm } from '@/hooks/use-ai'
import { useAuthStore } from '@/lib/auth-store'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { AiCommandResponse } from '@smartserve/types'

type EntryStatus = 'pending' | 'confirmed' | 'dismissed' | 'error'

interface HistoryEntry {
  id: string
  message: string
  status: EntryStatus
  response?: AiCommandResponse
  resultMessage?: string
}

const INTENT_LABELS: Record<string, string> = {
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

function confidenceColor(c: number) {
  if (c >= 0.85) return 'text-green-600'
  if (c >= 0.6) return 'text-amber-600'
  return 'text-red-500'
}

export default function AiPage() {
  const locationId = useAuthStore((s) => s.activeLocationId)
  const [input, setInput] = useState('')
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)
  const aiCommand = useAiCommand()
  const aiConfirm = useAiConfirm()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history])

  async function handleSend() {
    const message = input.trim()
    if (!message || !locationId) return

    const entryId = crypto.randomUUID()
    setHistory((h) => [...h, { id: entryId, message, status: 'pending' }])
    setInput('')

    try {
      const response = await aiCommand.mutateAsync({
        message,
        context: { locationId, currentScreen: 'ai' },
      })
      setHistory((h) =>
        h.map((e) => (e.id === entryId ? { ...e, status: 'pending', response } : e)),
      )
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed'
      setHistory((h) =>
        h.map((e) => (e.id === entryId ? { ...e, status: 'error', resultMessage: msg } : e)),
      )
    }
  }

  async function handleConfirm(entry: HistoryEntry) {
    if (!entry.response?.executionId) return
    try {
      const result = await aiConfirm.mutateAsync(entry.response.executionId)
      setHistory((h) =>
        h.map((e) =>
          e.id === entry.id
            ? { ...e, status: 'confirmed', resultMessage: result.message }
            : e,
        ),
      )
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed'
      setHistory((h) =>
        h.map((e) => (e.id === entry.id ? { ...e, status: 'error', resultMessage: msg } : e)),
      )
    }
  }

  function handleDismiss(id: string) {
    setHistory((h) => h.map((e) => (e.id === id ? { ...e, status: 'dismissed' } : e)))
  }

  const isLoading = aiCommand.isPending || aiConfirm.isPending

  return (
    <div className="p-6 flex flex-col h-[calc(100vh-4rem)] max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">AI Assistant</h1>

      {/* Conversation history */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {history.length === 0 && (
          <div className="text-center text-muted-foreground text-sm py-12 space-y-2">
            <p className="text-4xl">🤖</p>
            <p>Type a command in natural language.</p>
            <p className="text-xs">e.g. "Add margherita pizza for ₪58" or "הגדל את כל מחירי הפסטה ב-10%"</p>
          </div>
        )}

        {history.map((entry) => (
          <div key={entry.id} className="space-y-2">
            {/* User message */}
            <div className="flex justify-end">
              <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2 max-w-[80%] text-sm">
                {entry.message}
              </div>
            </div>

            {/* AI response */}
            {entry.status === 'pending' && !entry.response && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground pl-1">
                <span className="animate-pulse">●●●</span>
              </div>
            )}

            {entry.response && entry.status !== 'dismissed' && (
              <Card className={
                entry.status === 'confirmed' ? 'border-green-200 bg-green-50' :
                entry.status === 'error' ? 'border-red-200 bg-red-50' : ''
              }>
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        {INTENT_LABELS[entry.response.intent] ?? entry.response.intent}
                      </p>
                      <p className="text-sm">{entry.response.preview}</p>
                    </div>
                    <span className={`text-xs font-mono whitespace-nowrap ${confidenceColor(entry.response.confidence)}`}>
                      {Math.round(entry.response.confidence * 100)}%
                    </span>
                  </div>

                  {entry.status === 'confirmed' && (
                    <p className="text-xs text-green-700 font-medium">✓ {entry.resultMessage}</p>
                  )}
                  {entry.status === 'error' && (
                    <p className="text-xs text-red-600">{entry.resultMessage}</p>
                  )}

                  {entry.status === 'pending' && entry.response.requiresConfirmation && (
                    <div className="flex gap-2">
                      <Button size="sm" onClick={() => handleConfirm(entry)} disabled={isLoading}>
                        Confirm
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleDismiss(entry.id)}
                      >
                        Dismiss
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {entry.status === 'dismissed' && (
              <p className="text-xs text-muted-foreground pl-1">Dismissed.</p>
            )}

            {entry.status === 'error' && !entry.response && (
              <Card className="border-red-200 bg-red-50">
                <CardContent className="p-3">
                  <p className="text-xs text-red-600">{entry.resultMessage}</p>
                </CardContent>
              </Card>
            )}
          </div>
        ))}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="flex gap-2 pt-4 border-t">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
          placeholder="Type a command... (Enter to send)"
          disabled={isLoading}
          className="flex-1"
        />
        <Button onClick={handleSend} disabled={isLoading || !input.trim()}>
          {isLoading ? '…' : 'Send'}
        </Button>
      </div>
    </div>
  )
}
