import { useId, useRef, useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useLanguage } from '../hooks/useLanguage'
import { ApiError, generateText } from '../services/api'
import type { MarketingCampaign, TextGenerationRequest } from '../types/api'
import { marketingGenerationRequest } from '../utils/marketingGeneration'

function generationErrorKey(error: Error) {
  const status = error instanceof ApiError ? error.status : undefined
  switch (status) {
    case 404: return 'campaign.errMissing'
    case 422: return 'marketingGen.invalid'
    case 502: return 'marketingGen.rejected'
    case 503: return 'marketingGen.unavailable'
    case 504: return 'marketingGen.timeout'
    default: return 'marketingGen.failed'
  }
}

interface MarketingGenerationFormProps {
  targetAudience: string | null
  isPending: boolean
  isSuccess: boolean
  error: Error | null
  onGenerate: (data: TextGenerationRequest) => void
}

export function MarketingGenerationForm({
  targetAudience, isPending, isSuccess, error, onGenerate,
}: MarketingGenerationFormProps) {
  const { t } = useLanguage()
  const id = useId()
  const [override, setOverride] = useState('')
  const savedAudience = targetAudience?.trim() ?? ''
  const hasSavedAudience = savedAudience.length > 0 && Array.from(savedAudience).length <= 300
  const request = marketingGenerationRequest(override)
  const canGenerate = !isPending && (hasSavedAudience || Boolean(request.audience))

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (canGenerate) onGenerate(request)
  }

  return (
    <section className="card" aria-labelledby={`${id}-title`}>
      <div className="card__header">
        <h2 id={`${id}-title`}>{t('marketingGen.title')}</h2>
      </div>
      <div className="card__body">
        <form onSubmit={submit} aria-describedby={`${id}-cost`}>
          <p className="alert alert-info" id={`${id}-cost`} style={{ marginBottom: 16 }}>
            {t('marketingGen.cost')}
          </p>
          <div className="field">
            <label htmlFor={`${id}-audience`}>
              {t(hasSavedAudience ? 'marketingGen.override' : 'det.audience')}
            </label>
            <input
              id={`${id}-audience`}
              className="input"
              value={override}
              maxLength={300}
              required={!hasSavedAudience}
              disabled={isPending}
              dir="auto"
              aria-describedby={`${id}-audience-hint`}
              onChange={(event) => setOverride(event.target.value)}
            />
            <span className="hint" id={`${id}-audience-hint`}>
              {t(hasSavedAudience ? 'marketingGen.overrideHint' : 'marketingGen.audienceRequired')}
            </span>
          </div>
          {error && (
            <p className="alert alert-error" role="alert">{t(generationErrorKey(error))}</p>
          )}
          <div className="form-actions">
            <button type="submit" className="btn btn-gold" disabled={!canGenerate}>
              {t('marketingGen.generate')}
            </button>
            {isPending && <span className="spinner" aria-hidden="true" />}
          </div>
        </form>
        <div role="status">
          {isPending && <p className="muted" style={{ marginTop: 12 }}>{t('det.generating')}</p>}
          {isSuccess && (
            <p className="alert alert-info" style={{ marginTop: 12 }}>{t('marketingGen.saved')}</p>
          )}
        </div>
      </div>
    </section>
  )
}

export default function MarketingGeneration({ campaign }: { campaign: MarketingCampaign }) {
  const qc = useQueryClient()
  const inFlight = useRef(false)
  const [startError, setStartError] = useState<Error | null>(null)
  const contentsQuery = { queryKey: ['contents', campaign.id], exact: true }
  const generation = useMutation({
    mutationFn: (data: TextGenerationRequest) => generateText(campaign.id, data),
    onSuccess: async () => {
      await qc.cancelQueries(contentsQuery)
      await qc.invalidateQueries(contentsQuery)
    },
    onSettled: () => {
      inFlight.current = false
    },
  })

  function generate(data: TextGenerationRequest) {
    if (inFlight.current) return
    inFlight.current = true
    setStartError(null)
    try {
      generation.mutate(data)
    } catch {
      inFlight.current = false
      setStartError(new Error('Could not start generation'))
    }
  }

  return (
    <MarketingGenerationForm
      targetAudience={campaign.target_audience}
      isPending={generation.isPending}
      isSuccess={generation.isSuccess && !startError}
      error={startError ?? generation.error}
      onGenerate={generate}
    />
  )
}
