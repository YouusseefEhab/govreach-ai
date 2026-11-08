export type CampaignLanguage = 'arabic' | 'english' | 'both'

export interface Campaign {
  id: number
  title: string
  domain: string
  objective: string
  language: string
  status: string
  created_at: string
}

export interface CampaignCreate {
  title: string
  objective: string
  domain?: string
  language?: CampaignLanguage
}

export type CampaignUpdate = Partial<CampaignCreate> & { status?: 'draft' }

export interface TextPackage {
  headline: string
  slogan: string
  awareness_message: string
  social_caption: string
  call_to_action: string
}

export interface StoredContent {
  id: number
  campaign_id: number
  generation_id: string
  language: 'arabic' | 'english'
  content_type: 'text_package'
  review_status: 'draft' | 'approved' | 'rejected'
  content: TextPackage
  provider: string
  model: string
  prompt_version: string
  input_snapshot: Record<string, unknown>
  source_references: Record<string, unknown>[]
  created_at: string
}

export interface GenerationRequest {
  audience: string
  tone: 'informative' | 'encouraging' | 'formal'
}

export interface GenerationResponse {
  campaign_id: number
  contents: StoredContent[]
}

export type ContentUpdate =
  | { content: Partial<TextPackage>; review_status?: never }
  | { review_status: StoredContent['review_status']; content?: never }

export interface ImageGenerationRequest {
  source_content_id: number
  visual_brief: string
  style: 'illustration' | 'photorealistic'
}

export interface StoredImage {
  id: number
  campaign_id: number
  source_content_id: number
  idempotency_key: string
  request_state: 'reserved' | 'generating' | 'ready' | 'failed' | 'outcome_unknown'
  review_status: 'draft' | 'approved' | 'rejected'
  source_is_current: boolean
  source_snapshot: Record<string, unknown>
  source_references: Record<string, unknown>[]
  visual_brief: string
  style: string
  provider: string
  model: string
  prompt_version: string
  mime_type: 'image/png' | 'image/jpeg' | null
  width: number | null
  height: number | null
  byte_count: number | null
  failure_code: string | null
  created_at: string
  updated_at: string
}
