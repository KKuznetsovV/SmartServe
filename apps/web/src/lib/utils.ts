import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export { formatPrice } from '@smartserve/ui'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
