import { z } from 'zod'

export const ApiResponseSchema = <T extends z.ZodTypeAny>(dataSchema: T) =>
  z.object({
    data: dataSchema,
    meta: z
      .object({
        page: z.number().optional(),
        perPage: z.number().optional(),
        total: z.number().optional(),
      })
      .optional(),
  })

export const ApiErrorSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.unknown()).optional(),
  }),
})
export type ApiError = z.infer<typeof ApiErrorSchema>
