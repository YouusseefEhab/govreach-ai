// Types matching the FastAPI backend contract (app/schemas/*).

export type CampaignLanguage = 'arabic' | 'english' | 'both'
export type CampaignChannel = 'social' | 'email' | 'search' | 'website' | 'print'
export type BudgetCurrency = 'EGP' | 'USD'
export type OutputLanguage = 'arabic' | 'english'
export type ReviewStatus = 'draft' | 'approved' | 'rejected'
export type GenerationTone = 'informative' | 'encouraging' | 'formal'

export interface CampaignBudget {
  amount: string
  currency: BudgetCurrency
}

interface CampaignSummary {
  id: number
  title: string
  domain: string
  objective: string
  language: string
  status: string
  created_at: string
}

interface LegacyCampaign extends CampaignSummary {
  campaign_type?: null
}

export interface MarketingCampaign extends CampaignSummary {
  campaign_type: 'marketing'
  business_name: string | null
  offer_summary: string | null
  target_audience: string | null
  budget: CampaignBudget | null
  channels: CampaignChannel[] | null
  brief: string | null
}

export type Campaign = LegacyCampaign | MarketingCampaign

interface CampaignFields {
  title: string
  objective: string
  language?: CampaignLanguage
}

interface MarketingCampaignFields {
  business_name: string
  offer_summary: string
  target_audience: string
  budget?: CampaignBudget | null
  channels?: CampaignChannel[] | null
  brief?: string | null
}

export type CampaignCreate = CampaignFields & (
  | { campaign_type?: null; domain?: string }
  | ({ campaign_type: 'marketing' } & MarketingCampaignFields)
)

export type CampaignUpdate = Partial<CampaignFields & MarketingCampaignFields>

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
