import { z } from 'zod'
import { API_BASE_URL, ApiError, apiRequest } from './api.ts'
import type { ImageGenerationRequest, StoredImage } from './types.ts'

export const imageRequestSchema = z.object({
  source_content_id: z.number().int().positive(),
  visual_brief: z.string().trim().min(1, 'اكتب وصف للمشهد.').refine(
    (value) => [...value].length <= 2000, 'وصف المشهد لازم يكون ٢٠٠٠ حرف أو أقل.',
  ),
  style: z.enum(['illustration', 'photorealistic']),
}).strict()

const keySchema = z.string().regex(/^[A-Za-z0-9_-]{1,128}$/)
export const storedImageSchema = z.object({
  id: z.number().int().positive(), campaign_id: z.number().int().positive(),
  source_content_id: z.number().int().positive(), idempotency_key: keySchema,
  request_state: z.enum(['reserved', 'generating', 'ready', 'failed', 'outcome_unknown']),
  review_status: z.enum(['draft', 'approved', 'rejected']), source_is_current: z.boolean(),
  source_snapshot: z.record(z.string(), z.unknown()), source_references: z.array(z.record(z.string(), z.unknown())),
  visual_brief: z.string(), style: z.string(), provider: z.string(), model: z.string(), prompt_version: z.string(),
  mime_type: z.enum(['image/png', 'image/jpeg']).nullable(), width: z.number().int().positive().nullable(),
  height: z.number().int().positive().nullable(), byte_count: z.number().int().positive().nullable(),
  failure_code: z.string().nullable(), created_at: z.iso.datetime({ offset: true }), updated_at: z.iso.datetime({ offset: true }),
}).refine((row) => row.request_state === 'ready'
  ? row.mime_type !== null && row.width !== null && row.width === row.height && row.byte_count !== null
  : row.review_status === 'draft')

function validId(id: number) {
  if (!Number.isSafeInteger(id) || id <= 0) throw new Error('Invalid image identifier')
  return id
}

function imageError(error: unknown): never {
  if (error instanceof ApiError && error.status === 409) {
    throw new ApiError('النص أو حالة الطلب اتغيرت. حدّث الصور والنص قبل المتابعة.', 409, error.fields)
  }
  if (error instanceof ApiError && error.status === 422 && error.fields.length === 0) {
    throw new ApiError('طلب الصورة اترفض. جرّب وصف أقصر وراجع النص المختار.', 422)
  }
  throw error
}

export async function generateImage(campaignId: number, data: ImageGenerationRequest, key: string): Promise<StoredImage> {
  const request = imageRequestSchema.parse(data)
  keySchema.parse(key)
  validId(campaignId)
  const signal = AbortSignal.timeout(150_000)
  try {
    return await apiRequest(`/api/v1/campaigns/${campaignId}/generate-image`, {
      method: 'POST', headers: { 'Idempotency-Key': key }, body: JSON.stringify(request), signal,
    }, (body) => storedImageSchema.refine((row) => row.campaign_id === campaignId && row.idempotency_key === key
      && row.source_content_id === request.source_content_id).parse(body))
  } catch (error) {
    if (signal.aborted) throw new ApiError('انتظار الصورة انتهى. احتفظ بالطلب وراجع الصور المحفوظة قبل المتابعة.')
    return imageError(error)
  }
}

export function listImages(campaignId: number, skip = 0, limit = 20, signal?: AbortSignal): Promise<StoredImage[]> {
  return apiRequest(`/api/v1/campaigns/${validId(campaignId)}/images?${new URLSearchParams({ skip: String(skip), limit: String(limit) })}`,
    { signal }, (body) => z.array(storedImageSchema).refine((rows) => rows.every((row) => row.campaign_id === campaignId)).parse(body))
}

export function getImage(id: number, signal?: AbortSignal): Promise<StoredImage> {
  return apiRequest(`/api/v1/images/${validId(id)}`, { signal }, (body) => storedImageSchema.refine((row) => row.id === id).parse(body))
}

export async function reviewImage(id: number, status: StoredImage['review_status']): Promise<StoredImage> {
  z.enum(['draft', 'approved', 'rejected']).parse(status)
  try {
    return await apiRequest(`/api/v1/images/${validId(id)}`, { method: 'PATCH', body: JSON.stringify({ review_status: status }) },
      (body) => storedImageSchema.refine((row) => row.id === id && row.request_state === 'ready' && row.review_status === status
        && (status !== 'approved' || row.source_is_current)).parse(body))
  } catch (error) { return imageError(error) }
}

export function imageFileUrl(id: number, download = false) {
  return `${API_BASE_URL}/api/v1/images/${validId(id)}/file${download ? '?download=true' : ''}`
}

const attemptSchema = z.object({
  campaign_id: z.number().int().positive(), key: keySchema, request: imageRequestSchema,
  image_id: z.number().int().positive().optional(),
}).strict()
export type ImageAttempt = z.infer<typeof attemptSchema>
const attempts = new Map<number, ImageAttempt>()
const storageKey = (id: number) => `govreach-image-attempt-${id}`
type AttemptStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>
function tabStorage(): AttemptStorage | undefined {
  try { return typeof window === 'undefined' ? undefined : window.sessionStorage } catch { return undefined }
}

export function loadImageAttempt(id: number, storage = tabStorage()): ImageAttempt | null {
  try {
    const raw = storage?.getItem(storageKey(id))
    if (raw) {
      const saved = attemptSchema.parse(JSON.parse(raw))
      if (saved.campaign_id !== id) return null
      attempts.set(id, saved)
      return saved
    }
  } catch { /* Corrupt/blocked storage never starts a provider request. */ }
  return attempts.get(id) ?? null
}

export function saveImageAttempt(attempt: ImageAttempt, storage = tabStorage()): boolean {
  const saved = attemptSchema.parse(attempt)
  attempts.set(saved.campaign_id, saved)
  try {
    if (!storage) return false
    storage.setItem(storageKey(saved.campaign_id), JSON.stringify(saved))
    return true
  } catch { return false }
}

export function clearImageAttempt(id: number, storage = tabStorage()) {
  attempts.delete(id)
  try { storage?.removeItem(storageKey(id)) } catch { /* In-memory clearing remains available. */ }
}

export function createImageAttempt(campaignId: number, request: ImageGenerationRequest, makeKey = () => crypto.randomUUID()): ImageAttempt {
  return attemptSchema.parse({ campaign_id: campaignId, key: makeKey(), request: imageRequestSchema.parse(request) })
}
