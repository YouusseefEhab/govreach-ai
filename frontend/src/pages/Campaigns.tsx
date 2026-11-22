import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { deleteCampaign, listCampaigns } from '../services/api'
import { useLanguage } from '../hooks/useLanguage'
import StatusBadge from '../components/StatusBadge'
import type { Campaign } from '../types/api'
import { campaignLanguageLabel, campaignTypeLabel } from '../utils/campaignForm'

const LIMIT = 10

export default function Campaigns() {
  const { t, lang } = useLanguage()
  const qc = useQueryClient()
  const [page, setPage] = useState(0)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['campaigns', page],
    queryFn: () => listCampaigns(page * LIMIT, LIMIT),
  })

  const del = useMutation({
    mutationFn: deleteCampaign,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaigns'] }),
  })

  const onDelete = (c: Campaign) => {
    if (window.confirm(t('camp.confirmDelete'))) del.mutate(c.id)
  }

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString(lang === 'ar' ? 'ar-EG' : 'en-GB', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })

  return (
    <div className="stack">
      <div className="row between">
        <div>
          <h2 className="section-title">{t('camp.title')}</h2>
          <p className="section-sub">{t('camp.sub')}</p>
        </div>
        <Link to="/campaigns/new" className="btn btn-primary">
          + {t('camp.new')}
        </Link>
      </div>

      {del.isError && <p className="alert alert-error" role="alert">{t('campaign.errDelete')}</p>}
      <div className="card">
        {isLoading ? (
          <div className="state">
            <span className="spinner" />
            <span>{t('common.loading')}</span>
          </div>
        ) : isError ? (
          <div className="state">
            <p className="alert alert-error">{t('common.error')}</p>
          </div>
        ) : !data || data.length === 0 ? (
          <div className="state">
            <h3>{t('camp.empty')}</h3>
            <p className="muted">{t('camp.emptyHint')}</p>
            <Link to="/campaigns/new" className="btn btn-primary">
              {t('camp.new')}
            </Link>
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>{t('camp.col.title')}</th>
                <th>{t('camp.col.language')}</th>
                <th>{t('camp.col.status')}</th>
                <th>{t('camp.col.created')}</th>
                <th aria-label="actions" />
              </tr>
            </thead>
            <tbody>
              {data.map((c) => (
                <tr key={c.id}>
                  <td className="campaign-summary">
                    <div className="row-title"><bdi>{c.title}</bdi></div>
                    <div className="campaign-list-meta">
                      <span className="badge badge-neutral">{t(campaignTypeLabel(c))}</span>
                      {c.campaign_type === 'marketing' && c.business_name && <bdi>{c.business_name}</bdi>}
                    </div>
                    <div className="muted" style={{ fontSize: 13 }}>
                      <bdi>{c.objective}</bdi>
                    </div>
                  </td>
                  <td>{campaignLanguageLabel(c.language, t)}</td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                  <td>{formatDate(c.created_at)}</td>
                  <td>
                    <div className="row" style={{ justifyContent: 'flex-end' }}>
                      <Link
                        to={`/campaigns/${c.id}`}
                        className="btn btn-ghost btn-sm"
                      >
                        {t('camp.open')}
                      </Link>
                      <button
                        type="button"
                        className="btn btn-danger btn-sm"
                        onClick={() => onDelete(c)}
                        disabled={del.isPending}
                      >
                        {t('camp.delete')}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="pagination">
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => setPage((p) => Math.max(0, p - 1))}
          disabled={page === 0}
        >
          ← {t('camp.prev')}
        </button>
        <span className="muted">
          {t('camp.page')} {page + 1}
        </span>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() => setPage((p) => p + 1)}
          disabled={!data || data.length < LIMIT}
        >
          {t('camp.next')} →
        </button>
      </div>
    </div>
  )
}
