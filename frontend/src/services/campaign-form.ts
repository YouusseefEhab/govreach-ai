import { z } from 'zod'

export const campaignFormSchema = z.object({
  title: z.string().trim().min(1, 'اكتب اسم الحملة.').refine(
    (value) => [...value].length <= 255, 'اسم الحملة لازم يكون ٢٥٥ حرف أو أقل.',
  ),
  objective: z.string().trim().min(1, 'اكتب هدف واضح للحملة.'),
  language: z.enum(['arabic', 'english', 'both'], { error: 'اختار لغة المحتوى.' }),
})

export type CampaignFormValues = z.infer<typeof campaignFormSchema>
