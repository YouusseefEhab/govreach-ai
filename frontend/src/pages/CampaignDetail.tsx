import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  deleteCampaign,
  generateText,
  getCampaign,
  listContents,
  updateCampaign,
} from '../services/api'
import { useLanguage } from '../hooks/useLanguage'
import StatusBadge from '../components/StatusBadge'
import ContentPackage from '../components/ContentPackage'
import CampaignForm from '../components/CampaignForm'
import MarketingGeneration from '../components/MarketingGeneration'
import type { Campaign, CampaignUpdate, GeneratedContent, GenerationTone } from '../types/api'
import { campaignLanguageLabel, campaignTypeLabel } from '../utils/campaignForm'

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

function CampaignMetadata({ campaign }: { campaign: Campaign }) {
  const { t } = useLanguage()
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const update = useMutation({
    mutationFn: (data: CampaignUpdate) => updateCampaign(campaign.id, data),
    onSuccess: (saved) => {
      qc.setQueryData(['campaign', saved.id], saved)
      setEditing(false)
      void qc.invalidateQueries({ queryKey: ['campaign', saved.id] })
      void qc.invalidateQueries({ queryKey: ['campaigns'] })
    },
  })

  if (editing) {
    return (
      <CampaignForm
        campaign={campaign}
        isPending={update.isPending}
        error={update.error}
        onSubmit={(data) => update.mutate(data)}
        onCancel={() => setEditing(false)}
      />
    )
  }

  const marketing = campaign.campaign_type === 'marketing' ? campaign : undefined
  const fields = marketing ? [
    ['campaign.business', marketing.business_name],
    ['campaign.offer', marketing.offer_summary],
    ['campaign.audience', marketing.target_audience],
    ['campaign.budget', marketing.budget && `${marketing.budget.amount} ${marketing.budget.currency}`],
    ['campaign.channels', marketing.channels?.map((channel) => t(`campaign.channel.${channel}`)).join(' · ')],
    ['campaign.brief', marketing.brief],
  ] as const : []

  return (
    <>
      {fields.some(([, value]) => value) && (
        <dl className="campaign-metadata">
          {fields.map(([label, value]) => value && (
            <div key={label}>
              <dt>{t(label)}</dt>
              <dd><bdi>{value}</bdi></dd>
            </div>
          ))}
        </dl>
      )}
      {update.isSuccess && <p className="alert alert-info" role="status">{t('campaign.saved')}</p>}
      <button
        type="button"
        className="btn btn-ghost btn-sm"
        onClick={() => {
          update.reset()
          setEditing(true)
        }}
      >
        {t('campaign.edit')}
      </button>
    </>
  )
}

export default function CampaignDetail() {
  const { campaignId } = useParams()
  const id = Number(campaignId)
  const { t, lang } = useLanguage()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const { state } = useLocation()

  const { data: campaign, isLoading: cLoading, isError: cError } = useQuery({
    queryKey: ['campaign', id],
    queryFn: () => getCampaign(id),
    enabled: !!campaignId,
  })

  const { data: contents, isLoading: ctLoading } = useQuery({
    queryKey: ['contents', id],
    queryFn: ({ signal }) => listContents(id, undefined, undefined, signal),
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

      {state?.createdCampaignId === campaign.id && (
        <p className="alert alert-info" role="status">{t('campaign.created')}</p>
      )}

      {/* Campaign header */}
      <div className="card">
        <div className="card__header">
          <h2 style={{ fontSize: 20 }}><bdi>{campaign.title}</bdi></h2>
          <div style={{ marginInlineStart: 'auto' }} className="row">
            <StatusBadge status={campaign.status} />
            <span className="badge badge-neutral">{t(campaignTypeLabel(campaign))}</span>
            <span className="badge badge-neutral">{campaignLanguageLabel(campaign.language, t)}</span>
          </div>
        </div>
        <div className="card__body">
          <p className="campaign-summary" style={{ color: 'var(--ink-soft)' }}><bdi>{campaign.objective}</bdi></p>
          <CampaignMetadata key={campaign.id} campaign={campaign} />
          {del.isError && <p className="alert alert-error" role="alert">{t('campaign.errDelete')}</p>}
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
      {campaign.campaign_type === 'marketing' ? (
        <MarketingGeneration key={campaign.id} campaign={campaign} />
      ) : (
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
      )}

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
