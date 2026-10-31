import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { checkHealth } from '../services/api'
import { useLanguage } from '../hooks/useLanguage'

export default function Home() {
  const { t } = useLanguage()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['health'],
    queryFn: checkHealth,
  })
  const healthy = !isLoading && !isError && data?.status === 'healthy'
  const features = [
    { k: 'f1', title: t('home.f1.t'), desc: t('home.f1.d') },
    { k: 'f2', title: t('home.f2.t'), desc: t('home.f2.d') },
    { k: 'f3', title: t('home.f3.t'), desc: t('home.f3.d') },
    { k: 'f4', title: t('home.f4.t'), desc: t('home.f4.d') },
  ]

  return (
    <div className="stack">
      <section className="card">
        <div
          className="card__body"
          style={{ textAlign: 'center', padding: '48px 24px' }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              marginBottom: 16,
            }}
          >
            <img
              src="/logo.png"
              alt="Egyptian Smart Awareness Seal"
              style={{
                width: 120,
                height: 120,
                objectFit: 'contain',
                filter: 'drop-shadow(0 4px 12px rgba(200,164,76,0.35))',
              }}
            />
          </div>
          <p className="eyebrow">{t('home.eyebrow')}</p>
          <h1 style={{ fontSize: 'clamp(32px,5vw,52px)', margin: '12px 0' }}>
            {t('home.title')}
          </h1>
          <p
            style={{
              maxWidth: 640,
              margin: '0 auto',
              color: 'var(--ink-soft)',
              fontSize: 18,
            }}
          >
            {t('home.subtitle')}
          </p>
          <div className="row" style={{ justifyContent: 'center', marginTop: 24 }}>
            <Link to="/campaigns/new" className="btn btn-gold">
              {t('home.ctaPrimary')}
            </Link>
            <Link to="/campaigns" className="btn btn-ghost">
              {t('home.ctaSecondary')}
            </Link>
          </div>
          <p style={{ marginTop: 22 }}>
            <span className={`badge ${healthy ? 'badge-approved' : 'badge-draft'}`}>
              {isLoading
                ? t('common.loading')
                : healthy
                  ? t('home.status.ok')
                  : t('home.status.bad')}
            </span>
          </p>
        </div>
      </section>

      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))',
          gap: 16,
        }}
      >
        {features.map((f) => (
          <div key={f.k} className="card">
            <div className="card__body">
              <h3 style={{ fontSize: 16 }}>{f.title}</h3>
              <p style={{ color: 'var(--ink-soft)', fontSize: 14, margin: '6px 0 0' }}>
                {f.desc}
              </p>
            </div>
          </div>
        ))}
      </section>
    </div>
  )
}
