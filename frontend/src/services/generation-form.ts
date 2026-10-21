import { z } from 'zod'

export const generationFormSchema = z.object({
  audience: z.string().trim().min(1, 'حدّد الجمهور المستهدف.').refine(
    (value) => [...value].length <= 300, 'الجمهور المستهدف لازم يكون ٣٠٠ حرف أو أقل.',
  ),
  tone: z.enum(['informative', 'encouraging', 'formal'], { error: 'اختار نبرة الرسالة.' }),
})
