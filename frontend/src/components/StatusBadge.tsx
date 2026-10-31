import { useLanguage } from '../hooks/useLanguage'

export default function StatusBadge({ status }: { status: string }) {
  const { t } = useLanguage()
  const map: Record<string, { cls: string; label: string }> = {
    draft: { cls: 'badge-draft', label: t('common.draft') },
    approved: { cls: 'badge-approved', label: t('common.approved') },
    rejected: { cls: 'badge-rejected', label: t('common.rejected') },
  }
  const m = map[status] ?? { cls: 'badge-neutral', label: status }
  return <span className={`badge ${m.cls}`}>{m.label}</span>
}
