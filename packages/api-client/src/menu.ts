import type { MenuCategory, MenuItem, ModifierGroup } from '@smartserve/types'

import type { Http } from './client'

export function createMenuCategoriesResource(http: Http) {
  return {
    list: (locationId: string) => http.get<MenuCategory[]>(`/menu/locations/${locationId}/categories`),
    create: (data: Omit<MenuCategory, 'id'>) => http.post<MenuCategory>('/menu/categories', data),
    update: (id: string, data: Partial<MenuCategory>) => http.patch<MenuCategory>(`/menu/categories/${id}`, data),
    delete: (id: string) => http.del<void>(`/menu/categories/${id}`),
    reorder: (locationId: string, ids: string[]) =>
      http.post<void>(`/menu/locations/${locationId}/categories/reorder`, { ids }),
  }
}

export function createMenuItemsResource(http: Http) {
  return {
    list: (categoryId: string) => http.get<MenuItem[]>(`/menu/categories/${categoryId}/items`),
    get: (id: string) => http.get<MenuItem>(`/menu/items/${id}`),
    create: (data: Omit<MenuItem, 'id' | 'modifierGroups' | 'sortOrder'> & { sortOrder?: number }) =>
      http.post<MenuItem>('/menu/items', data),
    update: (id: string, data: Partial<MenuItem>) => http.patch<MenuItem>(`/menu/items/${id}`, data),
    delete: (id: string) => http.del<void>(`/menu/items/${id}`),
    setStock: (id: string, inStock: boolean) => http.patch<MenuItem>(`/menu/items/${id}/stock`, { inStock }),
    listStock: (locationId: string) => http.get<MenuItem[]>(`/menu/locations/${locationId}/stock`),
    reorder: (categoryId: string, ids: string[]) =>
      http.post<void>(`/menu/categories/${categoryId}/items/reorder`, { ids }),
  }
}

export function createModifierGroupsResource(http: Http) {
  return {
    create: (data: Omit<ModifierGroup, 'id'>) => http.post<ModifierGroup>('/menu/modifier-groups', data),
    update: (id: string, data: Partial<ModifierGroup>) =>
      http.patch<ModifierGroup>(`/menu/modifier-groups/${id}`, data),
    delete: (id: string) => http.del<void>(`/menu/modifier-groups/${id}`),
  }
}
