import type {
  Campaign,
  CampaignCreate,
  CampaignUpdate,
  ContentUpdate,
  GeneratedContent,
  SavedTextGeneration,
  TextGenerationRequest,
} from '../types/api'

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export class ApiError extends Error {
  status: number
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.name = 'ApiError'
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (body?.detail) {
        detail =
          typeof body.detail === 'string'
            ? body.detail
            : JSON.stringify(body.detail)
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export function checkHealth(): Promise<{ status: string }> {
  return request('/health')
}

export function listCampaigns(skip = 0, limit = 20): Promise<Campaign[]> {
  return request(`/api/v1/campaigns?skip=${skip}&limit=${limit}`)
}

export function getCampaign(id: number): Promise<Campaign> {
  return request(`/api/v1/campaigns/${id}`)
}

export function createCampaign(data: CampaignCreate): Promise<Campaign> {
  return request('/api/v1/campaigns', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateCampaign(id: number, data: CampaignUpdate): Promise<Campaign> {
  return request(`/api/v1/campaigns/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export function deleteCampaign(id: number): Promise<void> {
  return request(`/api/v1/campaigns/${id}`, { method: 'DELETE' })
}

export function generateText(
  campaignId: number,
  data: TextGenerationRequest,
): Promise<SavedTextGeneration> {
  return request(`/api/v1/campaigns/${campaignId}/generate-text`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function listContents(
  campaignId: number,
  skip = 0,
  limit = 100,
): Promise<GeneratedContent[]> {
  return request(
    `/api/v1/campaigns/${campaignId}/contents?skip=${skip}&limit=${limit}`,
  )
}

export function getContent(id: number): Promise<GeneratedContent> {
  return request(`/api/v1/contents/${id}`)
}

export function updateContent(
  id: number,
  data: ContentUpdate,
): Promise<GeneratedContent> {
  return request(`/api/v1/contents/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}
