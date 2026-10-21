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
