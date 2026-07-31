import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPrice(amount: number, currency = 'ILS'): string {
  return new Intl.NumberFormat('he-IL', { style: 'currency', currency }).format(amount)
}
