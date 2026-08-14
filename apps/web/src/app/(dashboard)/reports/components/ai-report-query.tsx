'use client'

import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Spinner } from '@/components/ui/spinner'
import { useAiCommand } from '@/hooks/use-ai'
import { useAuthStore } from '@/lib/auth-store'
import type { AiCommandResponse } from '@smartserve/types'
import { ClosedOrdersReportView } from './closed-orders-report-view'
import { SalesReportView } from './sales-report-view'
import { ServerSalesReportView } from './server-sales-report-view'

const EXAMPLES = [
  'What were my best-selling items last week?',
  'Who sold the most burgers this month?',
  'List all cancelled orders from yesterday',
]

function ReportResult({ response }: { response: AiCommandResponse }) {
  const { report } = response
  if (!report) return null

  if ('groupBy' in report) return <SalesReportView report={report} />
  if ('orders' in report) return <ClosedOrdersReportView report={report} />
  return <ServerSalesReportView report={report} />
}

/** Lets a manager ask for a report in plain language instead of using the manual
 * filters below — reuses the same read-only 'report.query' AI intent, which
 * returns its result inline (no /confirm step, since it never mutates data). */
export function AiReportQuery() {
  const locationId = useAuthStore((s) => s.activeLocationId)
  const [message, setMessage] = useState('')
  const [response, setResponse] = useState<AiCommandResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const aiCommand = useAiCommand()

  async function handleAsk() {
    const trimmed = message.trim()
    if (!trimmed || !locationId) return
    setError(null)
    setResponse(null)
    try {
      const result = await aiCommand.mutateAsync({
        message: trimmed,
        context: { locationId, currentScreen: 'reports' },
      })
      if (result.intent !== 'report.query' || !result.report) {
        setError("That didn't look like a report request. Try rephrasing, e.g. one of the examples below.")
        return
      }
      setResponse(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to run that report')
    }
  }

  return (
    <Card>
      <CardContent className="space-y-4 p-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <p className="text-sm font-medium">Ask AI for a report</p>
        </div>

        <div className="flex gap-2">
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
            placeholder="e.g. Show sales by category for March 1 to March 15"
            dir="auto"
          />
          <Button onClick={handleAsk} disabled={aiCommand.isPending || !message.trim()}>
            {aiCommand.isPending ? <Spinner className="h-4 w-4" /> : 'Ask'}
          </Button>
        </div>

        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              onClick={() => setMessage(example)}
              className="rounded-full border px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground"
            >
              {example}
            </button>
          ))}
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        {response?.report && (
          <div className="space-y-2 border-t pt-4">
            <p className="text-sm text-muted-foreground" dir="auto">
              {response.preview}
            </p>
            <ReportResult response={response} />
          </div>
        )}
      </CardContent>
    </Card>
  )
}
