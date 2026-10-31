// Types matching the FastAPI backend contract (app/schemas/*).

export type CampaignLanguage = 'arabic' | 'english' | 'both'
export type OutputLanguage = 'arabic' | 'english'
export type ReviewStatus = 'draft' | 'approved' | 'rejected'
export type GenerationTone = 'informative' | 'encouraging' | 'formal'

export interface Campaign {
  id: number
  title: string
  domain: string
  objective: string
  language: CampaignLanguage
  status: string
  created_at: string
}

export interface CampaignCreate {
  title: string
  objective: string
  language?: CampaignLanguage
  domain?: string
}

export interface CampaignUpdate {
  title?: string
  objective?: string
  language?: CampaignLanguage
  domain?: string
  status?: string
}

export interface TextPackage {
  headline: string
  slogan: string
  awareness_message: string
  social_caption: string
  call_to_action: string
}

export interface SourceReference {
  id: string
  topic: string
  title: string
  publisher: string
  url: string
  section: string
  checked_on: string
  facts: string[]
  catalogue_version?: string
  scope?: string
  usage?: string
}

export interface GeneratedContent {
  id: number
  campaign_id: number
  generation_id: string
  language: OutputLanguage
  content_type: string
  review_status: ReviewStatus
  content: TextPackage
  provider: string
  model: string
  prompt_version: string
  input_snapshot: Record<string, unknown>
  source_references: SourceReference[]
  created_at: string
}

export interface SavedTextGeneration {
  campaign_id: number
  contents: GeneratedContent[]
}

export interface TextGenerationRequest {
  audience: string
  tone?: GenerationTone
}

export interface ContentUpdate {
  content?: Partial<TextPackage>
  review_status?: ReviewStatus
}

export interface ApiError {
  detail: string
}
