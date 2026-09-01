'use client'

import { Download } from 'lucide-react'
import { toast } from 'sonner'
import { useTranslations } from 'next-intl'
import { Button } from '@/components/ui/button'
import { useExportReportCsv } from '@/hooks/use-reports'
import type { ExportReportParams } from '@smartserve/api-client'

export function CsvExportButton({ locationId, params }: { locationId: string; params: ExportReportParams }) {
  const t = useTranslations('reports')
  const exportCsv = useExportReportCsv()

  return (
    <Button
      size="sm"
      variant="outline"
      disabled={exportCsv.isPending}
      onClick={() =>
        exportCsv.mutate(
          { locationId, params },
          { onError: (err) => toast.error(err instanceof Error ? err.message : t('exportFailed')) },
        )
      }
    >
      <Download className="h-4 w-4" />
      {exportCsv.isPending ? t('exporting') : t('exportCsv')}
    </Button>
  )
}
