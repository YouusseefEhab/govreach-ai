import { useId, useState, type FormEvent } from 'react'
import { useLanguage } from '../hooks/useLanguage'
import { ApiError } from '../services/api'
import type { BudgetCurrency, Campaign, CampaignCreate, CampaignUpdate } from '../types/api'
import {
  campaignChanges,
  campaignChannels,
  campaignFormData,
  campaignFormValues,
  campaignLanguages,
  type CampaignFormValues,
} from '../utils/campaignForm'

type CampaignFormProps = {
  isPending: boolean
  error: Error | null
  onCancel: () => void
} & (
  | { campaign?: undefined; onSubmit: (data: CampaignCreate) => void }
  | { campaign: Campaign; onSubmit: (data: CampaignUpdate) => void }
)

interface TextFieldProps {
  label: string
  value: string
  error?: string
  hint?: string
  multiline?: boolean
  required?: boolean
  decimal?: boolean
  onChange: (value: string) => void
}

function TextField({ label, value, error, hint, multiline, required, decimal, onChange }: TextFieldProps) {
  const id = useId()
  const props = {
    id,
    value,
    required,
    dir: decimal ? 'ltr' : 'auto',
    'aria-invalid': Boolean(error),
    'aria-describedby': error ? `${id}-error` : hint ? `${id}-hint` : undefined,
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => onChange(e.target.value),
  } as const
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {multiline ? (
        <textarea className="textarea" {...props} />
      ) : (
        <input className="input" inputMode={decimal ? 'decimal' : undefined} {...props} />
      )}
      {hint && <span className="hint" id={`${id}-hint`}>{hint}</span>}
      {error && <span className="field-error" id={`${id}-error`}>{error}</span>}
    </div>
  )
}

export default function CampaignForm(props: CampaignFormProps) {
  const { t } = useLanguage()
  const id = useId()
  const [initialCampaign] = useState(() => props.campaign)
  const [values, setValues] = useState(() => campaignFormValues(initialCampaign))
  const [submitted, setSubmitted] = useState(false)
  const data = campaignFormData(values)
  const errors = submitted && 'errors' in data ? data.errors : {}
  const changes = initialCampaign && 'data' in data ? campaignChanges(initialCampaign, data.data) : undefined
  const marketing = values.kind === 'marketing'

  function setField<K extends keyof CampaignFormValues>(key: K, value: CampaignFormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }))
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitted(true)
    if (props.isPending || 'errors' in data) return
    if (!props.campaign) {
      props.onSubmit(data.data)
    } else if (changes && Object.keys(changes).length) {
      props.onSubmit(changes)
    }
  }

  const errorText = (field: keyof CampaignFormValues) => errors[field] ? t(errors[field]) : undefined
  const status = props.error instanceof ApiError ? props.error.status : undefined

  return (
    <form className="campaign-form" onSubmit={submit} noValidate aria-busy={props.isPending}>
      <fieldset disabled={props.isPending}>
        {!props.campaign && (
          <div className="field">
            <label htmlFor={`${id}-kind`}>{t('campaign.typeLabel')}</label>
            <select
              id={`${id}-kind`}
              className="select"
              value={values.kind}
              onChange={(event) => {
                setField('kind', event.target.value === 'marketing' ? 'marketing' : 'traffic_safety')
                setSubmitted(false)
              }}
            >
              <option value="marketing">{t('camp.type.marketing')}</option>
              <option value="traffic_safety">{t('camp.type.trafficSafety')}</option>
            </select>
          </div>
        )}
        <TextField
          label={t('new.titleLabel')}
          value={values.title}
          error={errorText('title')}
          onChange={(value) => setField('title', value)}
          required
        />
        <TextField
          label={t('new.objectiveLabel')}
          value={values.objective}
          error={errorText('objective')}
          hint={t(marketing ? 'campaign.objectiveHint' : 'new.objectiveHint')}
          onChange={(value) => setField('objective', value)}
          required
          multiline
        />
        <div className="field">
          <label htmlFor={`${id}-language`}>{t('new.languageLabel')}</label>
          <select
            id={`${id}-language`}
            className="select"
            value={values.language}
            aria-invalid={Boolean(errors.language)}
            aria-describedby={errors.language ? `${id}-language-error` : undefined}
            required
            onChange={(event) => setField('language', campaignLanguages.find((lang) => lang === event.target.value) ?? '')}
          >
            {!values.language && <option value="">{t('campaign.languageChoice')}</option>}
            {campaignLanguages.map((language) => (
              <option key={language} value={language}>{t(`lang.${language}`)}</option>
            ))}
          </select>
          {errors.language && <span className="field-error" id={`${id}-language-error`}>{t(errors.language)}</span>}
        </div>
        {marketing && (
          <>
            <TextField
              label={t('campaign.business')}
              value={values.business_name}
              error={errorText('business_name')}
              onChange={(value) => setField('business_name', value)}
              required
            />
            <TextField
              label={t('campaign.offer')}
              value={values.offer_summary}
              error={errorText('offer_summary')}
              onChange={(value) => setField('offer_summary', value)}
              required
              multiline
            />
            <TextField
              label={t('campaign.audience')}
              value={values.target_audience}
              error={errorText('target_audience')}
              onChange={(value) => setField('target_audience', value)}
              required
            />
            <div className="campaign-budget">
              <TextField
                label={t('campaign.budgetOptional')}
                value={values.budgetAmount}
                error={errorText('budgetAmount')}
                hint={props.campaign?.campaign_type === 'marketing' && props.campaign.budget ? t('campaign.clearBudget') : undefined}
                onChange={(value) => setField('budgetAmount', value)}
                decimal
              />
              <div className="field">
                <label htmlFor={`${id}-currency`}>{t('campaign.currency')}</label>
                <select
                  id={`${id}-currency`}
                  className="select"
                  value={values.budgetCurrency}
                  aria-invalid={Boolean(errors.budgetCurrency)}
                  aria-describedby={errors.budgetCurrency ? `${id}-currency-error` : undefined}
                  onChange={(event) => setField('budgetCurrency', event.target.value as BudgetCurrency | '')}
                >
                  <option value="">{t('campaign.currencyChoice')}</option>
                  <option value="EGP">{t('campaign.currency.EGP')}</option>
                  <option value="USD">{t('campaign.currency.USD')}</option>
                </select>
                {errors.budgetCurrency && (
                  <span className="field-error" id={`${id}-currency-error`}>{t(errors.budgetCurrency)}</span>
                )}
              </div>
            </div>
            <fieldset className="field campaign-channels">
              <legend>{t('campaign.channels')}</legend>
              <div className="row">
                {campaignChannels.map((channel) => (
                  <label key={channel}>
                    <input
                      type="checkbox"
                      checked={values.channels.includes(channel)}
                      onChange={(event) => setField('channels', event.target.checked
                        ? [...values.channels, channel]
                        : values.channels.filter((value) => value !== channel))}
                    />
                    {t(`campaign.channel.${channel}`)}
                  </label>
                ))}
              </div>
            </fieldset>
            <TextField
              label={t('campaign.briefOptional')}
              value={values.brief}
              error={errorText('brief')}
              onChange={(value) => setField('brief', value)}
              multiline
            />
          </>
        )}
        {props.error && (
          <p className="alert alert-error" role="alert">
            {t(status === 422 ? 'campaign.errRejected' : status === 404 ? 'campaign.errMissing' : 'campaign.errSave')}
          </p>
        )}
        <div className="form-actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={props.isPending || (changes && !Object.keys(changes).length)}
          >
            {props.campaign
              ? t(props.isPending ? 'det.saving' : 'det.save')
              : t(props.isPending ? 'new.creating' : 'new.create')}
          </button>
          <button type="button" className="btn btn-ghost" onClick={props.onCancel}>
            {t('new.cancel')}
          </button>
        </div>
      </fieldset>
    </form>
  )
}
