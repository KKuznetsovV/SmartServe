import type { Business, Location } from '@smartserve/types'

import type { Http } from './client'

export function createBusinessesResource(http: Http) {
  return {
    get: (id: string) => http.get<Business>(`/businesses/${id}`),
    update: (id: string, data: Partial<Business>) => http.patch<Business>(`/businesses/${id}`, data),
  }
}

export function createLocationsResource(http: Http) {
  return {
    list: (businessId: string) => http.get<Location[]>(`/businesses/${businessId}/locations`),
    get: (id: string) => http.get<Location>(`/locations/${id}`),
    create: (data: Omit<Location, 'id'>) => http.post<Location>('/locations', data),
    update: (id: string, data: Partial<Location>) => http.patch<Location>(`/locations/${id}`, data),
  }
}
