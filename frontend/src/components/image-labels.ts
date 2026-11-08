import { t } from '../i18n'
import type { StoredImage } from '../services/types'

export function imageStateLabel(state: StoredImage['request_state']) {
  return t({ reserved: 'الطلب محفوظ ولسه مبدأش', generating: 'جاري توليد الصورة', ready: 'الصورة جاهزة',
    failed: 'التوليد فشل', outcome_unknown: 'نتيجة الطلب غير مؤكدة' }[state])
}
