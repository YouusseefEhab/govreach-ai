import { z } from 'zod'
import type { Campaign, CampaignCreate, CampaignUpdate } from './types.ts'

const configuredBase = import.meta.env?.VITE_API_BASE_URL?.trim()
export const API_BASE_URL = (configuredBase || 'http://localhost:8000').replace(/\/+$/, '')

export interface FieldError {
  path: string
  message: string
}

export class ApiError extends Error {
  readonly status: number | null
  readonly fields: FieldError[]

  constructor(message: string, status: number | null = null, fields: FieldError[] = []) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fields = fields
  }
}

const statusMessages: Record<number, string> = {
  404: 'العنصر المطلوب مش موجود أو تم حذفه.',
  422: 'راجع البيانات المدخلة وحاول تاني.',
  502: 'مقدرناش نستخدم المحتوى اللي رجع من خدمة الذكاء الاصطناعي.',
  503: 'الخدمة مش متاحة دلوقتي. حاول كمان شوية.',
  504: 'طلب التوليد أخد وقت أطول من المتاح. راجع المحتوى المحفوظ قبل ما تعيد الطلب.',
}

const validationDetails = z.object({
  detail: z.array(z.object({
    loc: z.array(z.union([z.string(), z.number()])),
    msg: z.string(),
  })),
})

// One request only. Callers decide whether a read is safe to retry; mutations
// must never be replayed automatically, especially paid generation requests.
export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
  decode?: (value: unknown) => T,
): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')
  if (options.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  let response: Response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  } catch (error) {
    if (options.signal?.aborted || (error instanceof Error && error.name === 'AbortError')) {
      throw error
    }
    throw new ApiError('مش قادرين نتصل بالسيرفر. اتأكد إن FastAPI شغال وإن اتصالك سليم.')
  }

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const parsed = validationDetails.safeParse(body)
    const fields = response.status === 422 && parsed.success
      ? parsed.data.detail.map(({ loc, msg }) => ({
          path: loc.filter((part) => part !== 'body').join('.'),
          message: msg,
        }))
      : []
    throw new ApiError(
      statusMessages[response.status] || 'حصلت مشكلة في السيرفر. حاول تاني بعد شوية.',
      response.status,
      fields,
    )
  }

  if (response.status === 204) return undefined as T

  try {
    const body: unknown = await response.json()
    return decode ? decode(body) : body as T
  } catch {
    throw new ApiError('السيرفر رجّع بيانات غير متوقعة. جرّب تحديث الصفحة.', response.status)
  }
}

const healthSchema = z.object({ status: z.string().min(1) })
const campaignSchema = z.object({
  id: z.number().int().positive(),
  title: z.string(),
  objective: z.string(),
  domain: z.string(),
  language: z.string(),
  status: z.string(),
  created_at: z.iso.datetime({ offset: true }),
})

export function checkBackend(signal?: AbortSignal) {
  return apiRequest('/health', { signal }, (body) => healthSchema.parse(body))
}

export function listCampaigns(skip: number, limit: number, signal?: AbortSignal): Promise<Campaign[]> {
  const params = new URLSearchParams({ skip: String(skip), limit: String(limit) })
  return apiRequest(`/api/v1/campaigns?${params}`, { signal }, (body) => z.array(campaignSchema).parse(body))
}

export function getCampaign(id: number, signal?: AbortSignal): Promise<Campaign> {
  return apiRequest(`/api/v1/campaigns/${id}`, { signal }, (body) => campaignSchema.parse(body))
}

export function createCampaign(data: CampaignCreate): Promise<Campaign> {
  return apiRequest('/api/v1/campaigns', {
    method: 'POST', body: JSON.stringify(data),
  }, (body) => campaignSchema.parse(body))
}

export function updateCampaign(id: number, data: CampaignUpdate): Promise<Campaign> {
  return apiRequest(`/api/v1/campaigns/${id}`, {
    method: 'PATCH', body: JSON.stringify(data),
  }, (body) => campaignSchema.parse(body))
}

export function deleteCampaign(id: number): Promise<void> {
  return apiRequest(`/api/v1/campaigns/${id}`, { method: 'DELETE' })
}
