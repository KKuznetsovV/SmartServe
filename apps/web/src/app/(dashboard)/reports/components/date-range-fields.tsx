'use client'

import { useTranslations } from 'next-intl'
import { Label } from '@/components/ui/label'

interface DateRangeFieldsProps {
  startDate: string
  endDate: string
  onStartDateChange: (value: string) => void
  onEndDateChange: (value: string) => void
}

/** Two native date inputs (start/end) for filtering reports by day range.
 * Values are plain `YYYY-MM-DD` strings — converted to inclusive UTC
 * datetime bounds via `dayRangeToIso` before hitting the API. */
export function DateRangeFields({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
}: DateRangeFieldsProps) {
  const t = useTranslations('reports')
  return (
    <div className="flex items-end gap-3">
      <div className="space-y-1">
        <Label htmlFor="report-start-date">{t('from')}</Label>
        <input
          id="report-start-date"
          type="date"
          value={startDate}
          max={endDate}
          onChange={(e) => onStartDateChange(e.target.value)}
          className="border-input h-9 rounded-md border bg-transparent px-3 text-sm shadow-xs"
        />
      </div>
      <div className="space-y-1">
        <Label htmlFor="report-end-date">{t('to')}</Label>
        <input
          id="report-end-date"
          type="date"
          value={endDate}
          min={startDate}
          onChange={(e) => onEndDateChange(e.target.value)}
          className="border-input h-9 rounded-md border bg-transparent px-3 text-sm shadow-xs"
        />
      </div>
    </div>
  )
}
