import { z } from 'zod'
import type { Campaign, CampaignUpdate } from './types.ts'

export const campaignFormSchema = z.object({
  title: z.string().trim().min(1, 'اكتب اسم الحملة.').refine(
    (value) => [...value].length <= 255, 'اسم الحملة لازم يكون ٢٥٥ حرف أو أقل.',
  ),
  objective: z.string().trim().min(1, 'اكتب هدف واضح للحملة.'),
  language: z.enum(['arabic', 'english', 'both'], { error: 'اختار لغة المحتوى.' }),
})

export type CampaignFormValues = z.infer<typeof campaignFormSchema>

export function changedCampaignFields(original: Campaign, values: CampaignFormValues): CampaignUpdate {
  const changes: CampaignUpdate = {}
  if (values.title !== original.title) changes.title = values.title
  if (values.objective !== original.objective) changes.objective = values.objective
  if (values.language !== original.language) changes.language = values.language
  return changes
}
