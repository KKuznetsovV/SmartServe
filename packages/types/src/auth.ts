import { z } from 'zod'

export const UserRole = z.enum(['owner', 'manager', 'cashier', 'waiter', 'kitchen'])
export type UserRole = z.infer<typeof UserRole>

export const ROLE_RANK: Record<UserRole, number> = {
  owner: 4,
  manager: 3,
  cashier: 2,
  waiter: 1,
  kitchen: 0,
}

export function assignableRoles(actor: UserRole): UserRole[] {
  return UserRole.options.filter(
    (role) => ROLE_RANK[role] < ROLE_RANK[actor] || (actor === 'owner' && role === 'owner'),
  )
}

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
  userId: z.string().uuid(),
  pin: z.string().min(4).max(6).regex(/^\d{4,6}$/),
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

export const DeviceType = z.enum(['pos', 'kds', 'display'])
export type DeviceType = z.infer<typeof DeviceType>

export const DeviceSchema = z.object({
  id: z.string().uuid(),
  locationId: z.string().uuid(),
  name: z.string().min(1),
  type: DeviceType,
  createdBy: z.string().uuid(),
  lastSeenAt: z.string().nullable().optional(),
  revokedAt: z.string().nullable().optional(),
  createdAt: z.string(),
})
export type Device = z.infer<typeof DeviceSchema>

export const DeviceRegisterSchema = DeviceSchema.extend({
  token: z.string().min(1),
})
export type DeviceRegister = z.infer<typeof DeviceRegisterSchema>
