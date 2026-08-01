'use client'

import { useState, useRef, useEffect } from 'react'
import { toast } from 'sonner'
import { Paperclip, X, Trash2 } from 'lucide-react'
import { useAiCommand, useAiConfirm, useMenuImportUpload, useMenuImportMessage, useMenuImportApply } from '@/hooks/use-ai'
import { useAuthStore } from '@/lib/auth-store'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type { AiCommandResponse, MenuImportItem } from '@smartserve/types'

type EntryStatus = 'pending' | 'confirmed' | 'dismissed' | 'error'

interface HistoryEntry {
  id: string
  message: string
  status: EntryStatus
  response?: AiCommandResponse
  resultMessage?: string
  isImport?: boolean
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

const ACCEPTED_FILE_TYPES =
  'image/png,image/jpeg,image/webp,image/gif,application/pdf,text/csv,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.pdf,.csv,.txt,.docx'

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
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const aiCommand = useAiCommand()
  const aiConfirm = useAiConfirm()

  // Menu import (upload menu photo/PDF/sheet, converse with AI to organize it)
  const [importSessionId, setImportSessionId] = useState<string | null>(null)
  const [importNeedsClarification, setImportNeedsClarification] = useState(false)
  const [importItems, setImportItems] = useState<MenuImportItem[]>([])
  const uploadMenu = useMenuImportUpload()
  const importMessage = useMenuImportMessage()
  const importApply = useMenuImportApply()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history, importItems])

  // Auto-grow the textarea to fit pasted content (up to a max height, then it scrolls)
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 240)}px`
  }, [input])

  async function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !locationId) return

    const entryId = crypto.randomUUID()
    setHistory((h) => [...h, { id: entryId, message: `📎 ${file.name}`, status: 'pending', isImport: true }])

    try {
      const turn = await uploadMenu.mutateAsync({ locationId, file })
      setImportSessionId(turn.sessionId)
      setImportNeedsClarification(turn.needsClarification)
      setImportItems(turn.items)
      setHistory((h) =>
        h.map((e) => (e.id === entryId ? { ...e, status: 'confirmed', resultMessage: turn.message } : e)),
      )
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to read that file'
      setHistory((h) => h.map((e) => (e.id === entryId ? { ...e, status: 'error', resultMessage: msg } : e)))
    }
  }

  async function handleSend() {
    const message = input.trim()
    if (!message || !locationId) return
    setInput('')

    // While a menu import is in progress, the chat continues the import conversation
    if (importSessionId) {
      const entryId = crypto.randomUUID()
      setHistory((h) => [...h, { id: entryId, message, status: 'pending', isImport: true }])
      try {
        const turn = await importMessage.mutateAsync({ sessionId: importSessionId, message })
        setImportNeedsClarification(turn.needsClarification)
        setImportItems(turn.items)
        setHistory((h) =>
          h.map((e) => (e.id === entryId ? { ...e, status: 'confirmed', resultMessage: turn.message } : e)),
        )
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Failed'
        setHistory((h) => h.map((e) => (e.id === entryId ? { ...e, status: 'error', resultMessage: msg } : e)))
      }
      return
    }

    const entryId = crypto.randomUUID()
    setHistory((h) => [...h, { id: entryId, message, status: 'pending' }])

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

  function updateImportItem(index: number, patch: Partial<MenuImportItem>) {
    setImportItems((items) => items.map((it, i) => (i === index ? { ...it, ...patch } : it)))
  }

  function removeImportItem(index: number) {
    setImportItems((items) => items.filter((_, i) => i !== index))
  }

  function cancelImport() {
    setImportSessionId(null)
    setImportItems([])
    setImportNeedsClarification(false)
  }

  async function handleApplyImport() {
    if (!importSessionId || !locationId) return
    try {
      const result = await importApply.mutateAsync({ sessionId: importSessionId, items: importItems, locationId })
      toast.success(
        `Added ${result.itemsCreated} item(s) across ${result.categoriesCreated} new categor${result.categoriesCreated === 1 ? 'y' : 'ies'}, routed ${result.routesCreated} printer link(s)${result.unrouted.length ? `. No matching printer for: ${result.unrouted.join(', ')}` : ''}.`,
      )
      cancelImport()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to apply menu import')
    }
  }

  const isLoading = aiCommand.isPending || aiConfirm.isPending || uploadMenu.isPending || importMessage.isPending

  return (
    <div className="p-6 flex flex-col h-[calc(100vh-4rem)] max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">AI Assistant</h1>

      {/* Conversation history */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {history.length === 0 && (
          <div className="text-center text-muted-foreground text-sm py-12 space-y-2">
            <p className="text-4xl">🤖</p>
            <p>Type a command in natural language, or upload a menu file to import it.</p>
            <p className="text-xs">{'e.g. "Add margherita pizza for ₪58" or "הגדל את כל מחירי הפסטה ב-10%"'}</p>
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

            {entry.isImport && entry.resultMessage && (
              <div className="flex justify-start">
                <div
                  className={
                    entry.status === 'error'
                      ? 'bg-red-50 text-red-700 rounded-2xl rounded-tl-sm px-4 py-2 max-w-[80%] text-sm'
                      : 'bg-accent rounded-2xl rounded-tl-sm px-4 py-2 max-w-[80%] text-sm'
                  }
                >
                  {entry.resultMessage}
                </div>
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

            {entry.status === 'error' && !entry.response && !entry.isImport && (
              <Card className="border-red-200 bg-red-50">
                <CardContent className="p-3">
                  <p className="text-xs text-red-600">{entry.resultMessage}</p>
                </CardContent>
              </Card>
            )}
          </div>
        ))}

        {/* Active menu import review panel */}
        {importSessionId && (
          <Card className="border-primary/30">
            <CardContent className="p-4 space-y-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold">Menu import — review before applying</p>
                <Button size="sm" variant="ghost" onClick={cancelImport} title="Cancel import">
                  <X className="h-4 w-4" />
                </Button>
              </div>

              {importItems.length === 0 ? (
                <p className="text-sm text-muted-foreground">No items extracted yet.</p>
              ) : (
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {importItems.map((item, i) => (
                    <div key={i} className="grid grid-cols-[1fr_1fr_5rem_9rem_2rem] gap-2 items-center text-sm">
                      <Input
                        value={item.name}
                        onChange={(e) => updateImportItem(i, { name: e.target.value })}
                        placeholder="Item name"
                      />
                      <Input
                        value={item.category ?? ''}
                        onChange={(e) => updateImportItem(i, { category: e.target.value })}
                        placeholder="Category"
                      />
                      <Input
                        type="number"
                        value={item.price ?? ''}
                        onChange={(e) => updateImportItem(i, { price: Number(e.target.value) })}
                        placeholder="Price"
                      />
                      <div className="flex gap-2 text-xs">
                        {(['kitchen', 'receipt', 'label'] as const).map((type) => {
                          const active = item.printerTypes?.includes(type) ?? false
                          return (
                            <label key={type} className="flex items-center gap-1 cursor-pointer">
                              <input
                                type="checkbox"
                                className="h-3.5 w-3.5"
                                checked={active}
                                onChange={(e) => {
                                  const current = item.printerTypes ?? []
                                  const printerTypes = e.target.checked
                                    ? [...current, type]
                                    : current.filter((t) => t !== type)
                                  updateImportItem(i, { printerTypes })
                                }}
                              />
                              {type[0].toUpperCase()}
                            </label>
                          )
                        })}
                      </div>
                      <Button size="icon" variant="ghost" onClick={() => removeImportItem(i)} title="Remove item">
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex items-center justify-between gap-2 pt-2 border-t">
                <p className="text-xs text-muted-foreground">
                  {importNeedsClarification
                    ? 'Reply below to refine categories, prices, or printer routing.'
                    : `${importItems.length} item(s) ready to import.`}
                </p>
                <Button
                  size="sm"
                  onClick={handleApplyImport}
                  disabled={importApply.isPending || importItems.length === 0}
                >
                  {importApply.isPending ? 'Applying…' : 'Apply to Menu'}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="flex gap-2 pt-4 border-t items-end">
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_FILE_TYPES}
          className="hidden"
          onChange={handleFileSelect}
        />
        <Button
          type="button"
          variant="outline"
          size="icon"
          onClick={() => fileInputRef.current?.click()}
          disabled={isLoading}
          title="Upload a menu photo, PDF, or spreadsheet"
        >
          <Paperclip className="h-4 w-4" />
        </Button>
        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder={
            importSessionId
              ? 'Reply to continue the menu import... (Enter to send, Shift+Enter for a new line)'
              : 'Type a command or paste a whole menu... (Enter to send, Shift+Enter for a new line)'
          }
          disabled={isLoading}
          rows={1}
          className="flex-1 resize-none max-h-60 overflow-y-auto"
        />
        <Button onClick={handleSend} disabled={isLoading || !input.trim()}>
          {isLoading ? '…' : 'Send'}
        </Button>
      </div>
    </div>
  )
}

