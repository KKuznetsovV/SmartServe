'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { apiClient } from '@/lib/api'
import type { MenuCategory, MenuItem, ModifierGroup } from '@smartserve/types'

// ─── Categories ──────────────────────────────────────────────────────────────

export function useCategories(locationId: string | null) {
  return useQuery({
    queryKey: ['categories', locationId],
    queryFn: () => apiClient.menuCategories.list(locationId!),
    enabled: !!locationId,
  })
}

export function useCreateCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Omit<MenuCategory, 'id'>) => apiClient.menuCategories.create(data),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ['categories', variables.locationId] })
      toast.success('Category created')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUpdateCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<MenuCategory> }) =>
      apiClient.menuCategories.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['categories'] })
      toast.success('Category updated')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useDeleteCategory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiClient.menuCategories.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['categories'] })
      toast.success('Category deleted')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

// ─── Items ────────────────────────────────────────────────────────────────────

export function useMenuItems(categoryId: string | null) {
  return useQuery({
    queryKey: ['items', categoryId],
    queryFn: () => apiClient.menuItems.list(categoryId!),
    enabled: !!categoryId,
  })
}

export function useCreateMenuItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Omit<MenuItem, 'id' | 'modifierGroups'>) =>
      apiClient.menuItems.create(data),
    onSuccess: (_, variables) => {
      qc.invalidateQueries({ queryKey: ['items', variables.categoryId] })
      toast.success('Item created')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useUpdateMenuItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<MenuItem> }) =>
      apiClient.menuItems.update(id, data),
    onSuccess: (item) => {
      qc.invalidateQueries({ queryKey: ['items', item.categoryId] })
      toast.success('Item updated')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useDeleteMenuItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, categoryId }: { id: string; categoryId: string }) =>
      apiClient.menuItems.delete(id),
    onSuccess: (_, { categoryId }) => {
      qc.invalidateQueries({ queryKey: ['items', categoryId] })
      toast.success('Item deleted')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useToggleItemStock() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, inStock }: { id: string; inStock: boolean; categoryId: string }) =>
      apiClient.menuItems.toggle(id, inStock),
    onSuccess: (item) => {
      qc.invalidateQueries({ queryKey: ['items', item.categoryId] })
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

// ─── Modifier Groups ──────────────────────────────────────────────────────────

export function useCreateModifierGroup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Omit<ModifierGroup, 'id'>) =>
      apiClient.modifierGroups.create(data),
    onSuccess: (mg) => {
      qc.invalidateQueries({ queryKey: ['items', mg.itemId] })
      toast.success('Modifier group created')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}

export function useDeleteModifierGroup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, itemId }: { id: string; itemId: string }) =>
      apiClient.modifierGroups.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['items'] })
      toast.success('Modifier group deleted')
    },
    onError: (e: Error) => toast.error(e.message),
  })
}
