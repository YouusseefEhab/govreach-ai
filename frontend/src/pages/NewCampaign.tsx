import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import CampaignForm from '../components/CampaignForm'
import { createCampaign } from '../services/api'
import { useLanguage } from '../hooks/useLanguage'

export default function NewCampaign() {
  const { t } = useLanguage()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const create = useMutation({
    mutationFn: createCampaign,
    onSuccess: (campaign) => {
      qc.setQueryData(['campaign', campaign.id], campaign)
      void qc.invalidateQueries({ queryKey: ['campaigns'] })
      navigate(`/campaigns/${campaign.id}`, { state: { createdCampaignId: campaign.id } })
    },
  })

  return (
    <div className="stack" style={{ maxWidth: 640, margin: '0 auto' }}>
      <div>
        <h2 className="section-title">{t('new.title')}</h2>
        <p className="section-sub">{t('new.sub')}</p>
      </div>
      <div className="card">
        <div className="card__body">
          <CampaignForm
            isPending={create.isPending}
            error={create.error}
            onSubmit={(data) => create.mutate(data)}
            onCancel={() => navigate('/campaigns')}
          />
        </div>
      </div>
    </div>
  )
}
