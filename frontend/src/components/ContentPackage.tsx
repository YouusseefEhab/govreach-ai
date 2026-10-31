import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { GeneratedContent, TextPackage } from '../types/api'
import { updateContent } from '../services/api'
import { useLanguage } from '../hooks/useLanguage'
import StatusBadge from './StatusBadge'

const FIELD_KEYS: (keyof TextPackage)[] = [
  'headline',
  'slogan',
  'awareness_message',
  'social_caption',
  'call_to_action',
]

export default function ContentPackage({
  content,
  readOnly = false,
}: {
  content: GeneratedContent
  readOnly?: boolean
}) {
  const { t } = useLanguage()
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<TextPackage>(content.content)

  const invalidate = () =>
    qc.invalidateQueries({ queryKey: ['contents', content.campaign_id] })

  const save = useMutation({
    mutationFn: (data: Partial<TextPackage>) =>
      updateContent(content.id, { content: data }),
    onSuccess: () => {
      setEditing(false)
      invalidate()
    },
  })

  const review = useMutation({
    mutationFn: (status: 'approved' | 'rejected') =>
      updateContent(content.id, { review_status: status }),
    onSuccess: invalidate,
  })

  const changed: Partial<TextPackage> = {}
  for (const k of FIELD_KEYS) {
    if (draft[k] !== content.content[k]) changed[k] = draft[k]
  }

  const ar = content.language === 'arabic'
  const langName = ar ? 'العربية' : 'English'

  return (
    <div className={`pkg${ar ? ' ar' : ''}`} dir={ar ? 'rtl' : 'ltr'}>
      <div className="pkg__head">
        <span className="pkg__lang">
          {langName}
          <span className="muted" style={{ fontWeight: 400, fontSize: 12 }}>
            {' '}
            · {content.language}
          </span>
        </span>
        <StatusBadge status={content.review_status} />
      </div>

      <div className="pkg__body">
        {FIELD_KEYS.map((k) => (
          <div className="pkg__field" key={k}>
            <label>{t(`field.${k}`)}</label>
            {editing ? (
              <textarea
                className="textarea"
                value={draft[k]}
                rows={k === 'awareness_message' ? 4 : 2}
                onChange={(e) => setDraft({ ...draft, [k]: e.target.value })}
              />
            ) : (
              <span className="v">{content.content[k]}</span>
            )}
          </div>
        ))}

        {content.source_references.length > 0 && (
          <div className="sources" style={{ marginTop: 6 }}>
            <div className="muted" style={{ fontSize: 12, fontWeight: 700 }}>
              {t('det.sources')}
            </div>
            {content.source_references.map((s) => (
              <div className="source" key={s.id}>
                <div className="source__title">{s.title}</div>
                <div className="source__meta">
                  {s.publisher} · {s.section}
                </div>
                {s.facts.map((f, i) => (
                  <div
                    key={i}
                    style={{ fontSize: 13, color: 'var(--ink-soft)', marginTop: 4 }}
                  >
                    • {f}
                  </div>
                ))}
                <a
                  className="source__meta"
                  href={s.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {s.url}
                </a>
              </div>
            ))}
          </div>
        )}

        {!readOnly && (save.isError || review.isError) && (
          <p className="alert alert-error">{t('common.error')}</p>
        )}

        {!readOnly &&
          (editing ? (
            <div className="row" style={{ justifyContent: 'flex-end' }}>
              <button
                className="btn btn-ghost btn-sm"
                type="button"
                onClick={() => {
                  setEditing(false)
                  setDraft(content.content)
                }}
              >
                {t('det.cancel')}
              </button>
              <button
                className="btn btn-primary btn-sm"
                type="button"
                disabled={save.isPending || Object.keys(changed).length === 0}
                onClick={() => save.mutate(changed)}
              >
                {save.isPending ? t('det.saving') : t('det.save')}
              </button>
            </div>
          ) : (
            <div className="row between" style={{ flexWrap: 'wrap' }}>
              <span className="muted" style={{ fontSize: 12 }}>
                {t('det.reviewNote')}
              </span>
              <div className="row" style={{ justifyContent: 'flex-end' }}>
                <button
                  className="btn btn-ghost btn-sm"
                  type="button"
                  onClick={() => setEditing(true)}
                >
                  {t('det.edit')}
                </button>
                <button
                  className="btn btn-sm"
                  type="button"
                  disabled={review.isPending}
                  style={{
                    background: 'var(--approved-bg)',
                    color: 'var(--approved)',
                    border: '1px solid #bfe3c9',
                  }}
                  onClick={() => review.mutate('approved')}
                >
                  {t('det.approve')}
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  type="button"
                  disabled={review.isPending}
                  onClick={() => review.mutate('rejected')}
                >
                  {t('det.reject')}
                </button>
              </div>
            </div>
          ))}
      </div>
    </div>
  )
}
