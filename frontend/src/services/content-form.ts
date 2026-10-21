import { z } from 'zod'
import type { TextPackage } from './types.ts'

export const textFields = {
  headline: { label: 'العنوان', limit: 120 },
  slogan: { label: 'الشعار', limit: 100 },
  awareness_message: { label: 'رسالة التوعية', limit: 1200 },
  social_caption: { label: 'منشور التواصل الاجتماعي', limit: 600 },
  call_to_action: { label: 'الدعوة للفعل', limit: 200 },
} as const

const text = (limit: number) => z.string().trim().min(1, 'الحقل ده مطلوب.').refine(
  (value) => [...value].length <= limit, `الحد الأقصى ${limit} حرف.`,
)
export const contentFormSchema = z.object({
  headline: text(120), slogan: text(100), awareness_message: text(1200),
  social_caption: text(600), call_to_action: text(200),
})

export function changedTextFields(saved: TextPackage, values: TextPackage): Partial<TextPackage> {
  return Object.fromEntries((Object.keys(textFields) as (keyof TextPackage)[])
    .filter((field) => saved[field] !== values[field]).map((field) => [field, values[field]]))
}
