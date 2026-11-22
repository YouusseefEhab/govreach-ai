import type {
  BudgetCurrency,
  Campaign,
  CampaignChannel,
  CampaignCreate,
  CampaignLanguage,
  CampaignUpdate,
} from '../types/api'

export const campaignLanguages = ['both', 'arabic', 'english'] as const
export const campaignChannels = ['social', 'email', 'search', 'website', 'print'] as const

export interface CampaignFormValues {
  kind: 'marketing' | 'traffic_safety'
  title: string
  objective: string
  language: CampaignLanguage | ''
  business_name: string
  offer_summary: string
  target_audience: string
  budgetAmount: string
  budgetCurrency: BudgetCurrency | ''
  channels: CampaignChannel[]
  brief: string
}

export type CampaignFormErrors = Partial<Record<keyof CampaignFormValues, string>>

export function campaignTypeLabel(campaign: Campaign) {
  if (campaign.campaign_type === 'marketing') return 'camp.type.marketing'
  return campaign.domain === 'traffic_safety' ? 'camp.type.trafficSafety' : 'camp.type.legacy'
}

export function campaignLanguageLabel(language: string, t: (key: string) => string) {
  const option = campaignLanguages.find((value) => value === language)
  return option ? t(`lang.${option}`) : language
}

export function campaignFormValues(campaign?: Campaign): CampaignFormValues {
  const marketing = campaign?.campaign_type === 'marketing' ? campaign : undefined
  return {
    kind: campaign && !marketing ? 'traffic_safety' : 'marketing',
    title: campaign?.title ?? '',
    objective: campaign?.objective ?? '',
    language: campaign ? campaignLanguages.find((value) => value === campaign.language) ?? '' : 'both',
    business_name: marketing?.business_name ?? '',
    offer_summary: marketing?.offer_summary ?? '',
    target_audience: marketing?.target_audience ?? '',
    budgetAmount: marketing?.budget?.amount ?? '',
    budgetCurrency: marketing?.budget?.currency ?? '',
    channels: marketing?.channels ?? [],
    brief: marketing?.brief ?? '',
  }
}

const budgetPattern = /^[0-9]{1,12}(\.[0-9]{1,2})?$/
const localDigits = '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹'
const asciiDigits = '01234567890123456789'

function budgetAmount(value: string) {
  return value.trim()
    .replace(/[٠-٩۰-۹]/g, (digit) => asciiDigits[localDigits.indexOf(digit)])
    .replaceAll('٫', '.')
}

function textLength(value: string) {
  return Array.from(value).length
}

export function campaignFormData(
  values: CampaignFormValues,
): { data: CampaignCreate } | { errors: CampaignFormErrors } {
  const errors: CampaignFormErrors = {}
  const title = values.title.trim()
  const objective = values.objective.trim()
  const language = values.language
  if (!title || textLength(title) > 255) errors.title = 'new.errTitle'
  if (!objective) errors.objective = 'new.errObjective'
  if (!language) errors.language = 'campaign.errLanguage'

  if (values.kind === 'traffic_safety') {
    return !language || Object.keys(errors).length ? { errors } : { data: { title, objective, language } }
  }

  const business_name = values.business_name.trim()
  const offer_summary = values.offer_summary.trim()
  const target_audience = values.target_audience.trim()
  const brief = values.brief.trim()
  const amount = budgetAmount(values.budgetAmount)
  if (textLength(objective) > 2000) errors.objective = 'campaign.errMarketingObjective'
  if (!business_name || textLength(business_name) > 120) errors.business_name = 'campaign.errBusiness'
  if (!offer_summary || textLength(offer_summary) > 1000) errors.offer_summary = 'campaign.errOffer'
  if (!target_audience || textLength(target_audience) > 300) errors.target_audience = 'campaign.errAudience'
  if (textLength(brief) > 3000) errors.brief = 'campaign.errBrief'
  if (amount && !budgetPattern.test(amount)) errors.budgetAmount = 'campaign.errBudget'
  if (amount && !values.budgetCurrency) errors.budgetCurrency = 'campaign.errCurrency'
  if (!language || Object.keys(errors).length) return { errors }

  return {
    data: {
      campaign_type: 'marketing',
      title,
      objective,
      language,
      business_name,
      offer_summary,
      target_audience,
      budget: amount && values.budgetCurrency ? { amount, currency: values.budgetCurrency } : null,
      channels: values.channels,
      brief: brief || null,
    },
  }
}

export function campaignChanges(campaign: Campaign, data: CampaignCreate): CampaignUpdate {
  const changes: CampaignUpdate = {}
  if (data.title !== campaign.title) changes.title = data.title
  if (data.objective !== campaign.objective) changes.objective = data.objective
  if (data.language !== campaign.language) changes.language = data.language
  if (campaign.campaign_type !== 'marketing' || data.campaign_type !== 'marketing') return changes

  for (const field of ['business_name', 'offer_summary', 'target_audience'] as const) {
    if (data[field] !== campaign[field]) changes[field] = data[field]
  }
  if (data.brief !== (campaign.brief || null)) changes.brief = data.brief
  if (data.channels?.join() !== (campaign.channels ?? []).join()) changes.channels = data.channels
  if (data.budget?.amount !== campaign.budget?.amount || data.budget?.currency !== campaign.budget?.currency) {
    changes.budget = data.budget ?? null
  }
  return changes
}
