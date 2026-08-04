import type { Printer, PrinterRoute } from '@smartserve/types'

import type { Http } from './client'

export function createPrintersResource(http: Http) {
  return {
    list: (locationId: string) => http.get<Printer[]>(`/locations/${locationId}/printers`),
    create: (data: Omit<Printer, 'id'>) => http.post<Printer>('/printers', data),
    update: (id: string, data: Partial<Printer>) => http.patch<Printer>(`/printers/${id}`, data),
    delete: (id: string) => http.del<void>(`/printers/${id}`),
    listRoutes: (locationId: string) => http.get<PrinterRoute[]>(`/locations/${locationId}/printer-routes`),
    addRoute: (printerId: string, itemId: string) =>
      http.post<PrinterRoute>('/printer-routes', { printerId, itemId }),
    deleteRoute: (routeId: string) => http.del<void>(`/printer-routes/${routeId}`),
  }
}
