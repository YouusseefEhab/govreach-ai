import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { createCampaign } from '../services/api'
import { useLanguage } from '../hooks/useLanguage'
import type { CampaignLanguage } from '../types/api'

export default function NewCampaign() {
  const { t } = useLanguage()
  const navigate = useNavigate()

  const [title, setTitle] = useState('')
  const [objective, setObjective] = useState('')
  const [language, setLanguage] = useState<CampaignLanguage>('both')
  const [errors, setErrors] = useState<{ title?: string; objective?: string }>({})

  const create = useMutation({
    mutationFn: () =>
      createCampaign({ title: title.trim(), objective: objective.trim(), language }),
    onSuccess: (c) => navigate(`/campaigns/${c.id}`),
  })

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const next: typeof errors = {}
    if (title.trim().length < 1 || title.trim().length > 255)
      next.title = t('new.errTitle')
    if (objective.trim().length < 1) next.objective = t('new.errObjective')
    setErrors(next)
    if (Object.keys(next).length === 0) create.mutate()
  }

  return (
    <div className="stack" style={{ maxWidth: 640, margin: '0 auto' }}>
      <div>
        <h2 className="section-title">{t('new.title')}</h2>
        <p className="section-sub">{t('new.sub')}</p>
      </div>

      <form className="card" onSubmit={submit} noValidate>
        <div className="card__body">
          <div className="field">
            <label htmlFor="title">{t('new.titleLabel')}</label>
            <input
              id="title"
              className="input"
              value={title}
              maxLength={255}
              onChange={(e) => setTitle(e.target.value)}
              aria-invalid={!!errors.title}
            />
            {errors.title && <span className="field-error">{errors.title}</span>}
          </div>

          <div className="field">
            <label htmlFor="objective">{t('new.objectiveLabel')}</label>
            <textarea
              id="objective"
              className="textarea"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              aria-invalid={!!errors.objective}
            />
            <span className="hint">{t('new.objectiveHint')}</span>
            {errors.objective && (
              <span className="field-error">{errors.objective}</span>
            )}
          </div>

          <div className="field">
            <label htmlFor="language">{t('new.languageLabel')}</label>
            <select
              id="language"
              className="select"
              value={language}
              onChange={(e) => setLanguage(e.target.value as CampaignLanguage)}
            >
              <option value="both">{t('lang.both')}</option>
              <option value="arabic">{t('lang.arabic')}</option>
              <option value="english">{t('lang.english')}</option>
            </select>
          </div>

          {create.isError && (
            <p className="alert alert-error" style={{ marginBottom: 16 }}>
              {t('common.error')}
            </p>
          )}

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={create.isPending}>
              {create.isPending ? t('new.creating') : t('new.create')}
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => navigate('/campaigns')}
            >
              {t('new.cancel')}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
