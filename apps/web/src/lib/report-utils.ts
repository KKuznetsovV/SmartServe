/** Converts a pair of `YYYY-MM-DD` date-input values into an inclusive UTC
 * datetime range (`start` at 00:00:00.000, `end` at 23:59:59.999) matching
 * what services/reporting's `start`/`end <=`/`>=` query params expect. */
export function dayRangeToIso(startDate: string, endDate: string): { start: string; end: string } {
  return {
    start: `${startDate}T00:00:00.000Z`,
    end: `${endDate}T23:59:59.999Z`,
  }
}

/** Triggers a browser download of an in-memory blob (e.g. a CSV export) without
 * navigating away from the current page. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
