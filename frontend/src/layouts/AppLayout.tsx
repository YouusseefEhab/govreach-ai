import { NavLink, Outlet } from 'react-router-dom'
import { useLanguage } from '../hooks/useLanguage'

export default function AppLayout() {
  const { lang, setLang, t } = useLanguage()
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? 'active' : ''

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__inner">
          <NavLink to="/" className="brand">
            <span className="brand__emblem" aria-hidden="true">
              <img
                src="/logo.png"
                alt="Egyptian Smart Awareness Seal"
                style={{ width: 38, height: 38, objectFit: 'contain' }}
              />
            </span>
            <span className="brand__title">
              <b>GovReach AI</b>
              <span>{t('brand.tagline')}</span>
            </span>
          </NavLink>
          <nav className="app-nav" aria-label="Primary">
            <NavLink to="/" end className={linkClass}>
              {t('nav.home')}
            </NavLink>
            <NavLink to="/campaigns" className={linkClass}>
              {t('nav.campaigns')}
            </NavLink>
            <NavLink to="/campaigns/new" className={linkClass}>
              {t('nav.new')}
            </NavLink>
          </nav>
          <div className="lang-toggle" role="group" aria-label="Interface language">
            <button
              type="button"
              className={lang === 'en' ? 'active' : ''}
              onClick={() => setLang('en')}
              aria-pressed={lang === 'en'}
            >
              {t('lang.en')}
            </button>
            <button
              type="button"
              className={lang === 'ar' ? 'active' : ''}
              onClick={() => setLang('ar')}
              aria-pressed={lang === 'ar'}
            >
              {t('lang.ar')}
            </button>
          </div>
        </div>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
      <footer className="app-footer">
        <p className="disclaimer">{t('home.disclaimer')}</p>
        <p style={{ marginTop: 6 }}>GovReach AI — graduation prototype</p>
      </footer>
    </div>
  )
}
