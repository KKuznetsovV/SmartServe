import { z } from 'zod'

export const UserRole = z.enum(['owner', 'manager', 'cashier', 'waiter', 'kitchen'])
export type UserRole = z.infer<typeof UserRole>

export const UserSchema = z.object({
  id: z.string().uuid(),
  businessId: z.string().uuid(),
  email: z.string().email().optional(),
  name: z.string().min(1),
  role: UserRole,
  language: z.enum(['he', 'en']).default('he'),
  active: z.boolean().default(true),
})
export type User = z.infer<typeof UserSchema>

export const LoginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
})
export type Login = z.infer<typeof LoginSchema>

export const PinLoginSchema = z.object({
  locationId: z.string().uuid(),
  pin: z.string().length(4).regex(/^\d{4}$/),
})
export type PinLogin = z.infer<typeof PinLoginSchema>

export const PinStaffSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  role: UserRole,
})
export type PinStaff = z.infer<typeof PinStaffSchema>

export const TokenPairSchema = z.object({
  accessToken: z.string(),
  refreshToken: z.string(),
  expiresIn: z.number(),
})
export type TokenPair = z.infer<typeof TokenPairSchema>
