import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  deleteCampaign,
  generateText,
  getCampaign,
  listContents,
} from '../services/api'
import { useLanguage } from '../hooks/useLanguage'
import StatusBadge from '../components/StatusBadge'
import ContentPackage from '../components/ContentPackage'
import type { GeneratedContent, GenerationTone } from '../types/api'

interface Generation {
  id: string
  items: GeneratedContent[]
  created: string
  provider: string
  model: string
  prompt: string
}

function groupGenerations(contents: GeneratedContent[]): Generation[] {
  const map = new Map<string, GeneratedContent[]>()
  for (const c of contents) {
    const arr = map.get(c.generation_id) ?? []
    arr.push(c)
    map.set(c.generation_id, arr)
  }
  const gens: Generation[] = []
  for (const [id, items] of map) {
    const first = items[0]
    gens.push({
      id,
      items,
      created: first.created_at,
      provider: first.provider,
      model: first.model,
      prompt: first.prompt_version,
    })
  }
  return gens.sort((a, b) => b.created.localeCompare(a.created))
}

export default function CampaignDetail() {
  const { campaignId } = useParams()
  const id = Number(campaignId)
  const { t, lang } = useLanguage()
  const qc = useQueryClient()
  const navigate = useNavigate()

  const { data: campaign, isLoading: cLoading, isError: cError } = useQuery({
    queryKey: ['campaign', id],
    queryFn: () => getCampaign(id),
    enabled: !!campaignId,
  })

  const { data: contents, isLoading: ctLoading } = useQuery({
    queryKey: ['contents', id],
    queryFn: () => listContents(id),
    enabled: !!campaignId,
  })

  const [audience, setAudience] = useState('')
  const [tone, setTone] = useState<GenerationTone>('informative')

  const gen = useMutation({
    mutationFn: () => generateText(id, { audience: audience.trim(), tone }),
    onSuccess: () => {
      setAudience('')
      qc.invalidateQueries({ queryKey: ['contents', id] })
    },
  })

  const del = useMutation({
    mutationFn: () => deleteCampaign(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] })
      navigate('/campaigns')
    },
  })

  const fmt = (iso: string) =>
    new Date(iso).toLocaleString(lang === 'ar' ? 'ar-EG' : 'en-GB', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })

  const generations = contents ? groupGenerations(contents) : []

  if (cLoading) {
    return (
      <div className="state">
        <span className="spinner" />
        <span>{t('common.loading')}</span>
      </div>
    )
  }
  if (cError || !campaign) {
    return (
      <div className="state">
        <p className="alert alert-error">{t('common.error')}</p>
        <Link to="/campaigns" className="btn btn-ghost">
          {t('det.back')}
        </Link>
      </div>
    )
  }

  return (
    <div className="stack">
      <div>
        <Link to="/campaigns" className="muted" style={{ fontSize: 14 }}>
          ← {t('det.back')}
        </Link>
      </div>

      {/* Campaign header */}
      <div className="card">
        <div className="card__header">
          <h2 style={{ fontSize: 20 }}>{campaign.title}</h2>
          <div style={{ marginInlineStart: 'auto' }} className="row">
            <StatusBadge status={campaign.status} />
            <span className="badge badge-neutral">{campaign.domain}</span>
            <span className="badge badge-neutral">{campaign.language}</span>
          </div>
        </div>
        <div className="card__body">
          <p style={{ color: 'var(--ink-soft)' }}>{campaign.objective}</p>
          <div className="row between" style={{ marginTop: 16 }}>
            <span className="muted" style={{ fontSize: 13 }}>
              {t('camp.col.created')}: {fmt(campaign.created_at)}
            </span>
            <button
              type="button"
              className="btn btn-danger btn-sm"
              disabled={del.isPending}
              onClick={() => {
                if (window.confirm(t('det.confirmDelete'))) del.mutate()
              }}
            >
              {t('det.delete')}
            </button>
          </div>
        </div>
      </div>

      {/* Generate form */}
      <div className="card">
        <div className="card__header">
          <h2 style={{ fontSize: 18 }}>{t('det.generate')}</h2>
        </div>
        <div className="card__body">
          <div className="field">
            <label htmlFor="audience">{t('det.audience')}</label>
            <input
              id="audience"
              className="input"
              value={audience}
              maxLength={300}
              placeholder={t('det.audienceHint')}
              onChange={(e) => setAudience(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="tone">{t('det.tone')}</label>
            <select
              id="tone"
              className="select"
              value={tone}
              onChange={(e) => setTone(e.target.value as GenerationTone)}
              style={{ maxWidth: 240 }}
            >
              <option value="informative">{t('det.tone.informative')}</option>
              <option value="encouraging">{t('det.tone.encouraging')}</option>
              <option value="formal">{t('det.tone.formal')}</option>
            </select>
          </div>

          {gen.isError && (
            <p className="alert alert-error" style={{ marginBottom: 16 }}>
              {gen.error instanceof Error ? gen.error.message : t('common.error')}
            </p>
          )}

          <div className="form-actions">
            <button
              type="button"
              className="btn btn-gold"
              disabled={gen.isPending || audience.trim().length === 0}
              onClick={() => gen.mutate()}
            >
              {gen.isPending ? t('det.generating') : t('det.generate')}
            </button>
            {gen.isPending && <span className="spinner" />}
          </div>
        </div>
      </div>

      {/* Drafts */}
      {ctLoading ? (
        <div className="state">
          <span className="spinner" />
          <span>{t('common.loading')}</span>
        </div>
      ) : generations.length === 0 ? (
        <div className="card">
          <div className="state">
            <p className="muted">{t('det.noContent')}</p>
          </div>
        </div>
      ) : (
        <>
          <div>
            <h2 className="section-title">{t('det.drafts')}</h2>
          </div>
          {generations[0].items.map((c) => (
            <ContentPackage key={c.id} content={c} />
          ))}

          {generations.length > 1 && (
            <>
              <h2 className="section-title" style={{ marginTop: 12 }}>
                {t('det.history')}
              </h2>
              {generations.slice(1).map((g) => (
                <div className="stack" key={g.id}>
                  <div className="muted" style={{ fontSize: 13 }}>
                    {fmt(g.created)} · {t('det.meta.provider')}: {g.provider} ·{' '}
                    {t('det.meta.model')}: {g.model}
                  </div>
                  {g.items.map((c) => (
                    <ContentPackage key={c.id} content={c} readOnly />
                  ))}
                </div>
              ))}
            </>
          )}
        </>
      )}
    </div>
  )
}
