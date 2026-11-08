import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useLanguage } from '../hooks/useLanguage'
import { t as translate } from '../i18n'
import { messages } from '../messages'
import { healthQuery } from '../queries'

export default function AppLayout() {
  const { lang, setLang, t } = useLanguage()
  const { pathname } = useLocation()
  const mainRef = useRef<HTMLElement>(null)
  const previousPath = useRef(pathname)
  const health = useQuery(healthQuery)
  const available = health.isSuccess && health.data.status === 'healthy'
  const status = health.isPending ? translate(messages.checking) : available ? translate(messages.connected) : translate(messages.disconnected)
  useEffect(() => {
    document.documentElement.lang = lang === 'ar' ? 'ar-EG' : 'en'
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr'
    document.title = `${pathname.startsWith('/contents/') ? translate('مراجعة المحتوى') : pathname.startsWith('/campaigns') ? translate(messages.campaigns) : translate(messages.home)} | GovReach AI`
    if (previousPath.current !== pathname) {
      mainRef.current?.focus()
      previousPath.current = pathname
    }
  }, [pathname, lang])
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? 'active' : ''

  return (
    <div className="app">
      <a className="skip-link" href="#main">{translate(messages.skipLink)}</a>
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
          <nav className="app-nav" aria-label={translate(messages.navigation)}>
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
          <div className="lang-toggle" role="group" aria-label="لغة الواجهة / Interface language">
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
      <div className="workspace-status">
        <span>{translate('مساحة عمل الحملات')}</span>
        <span className={`connection ${available ? 'online' : ''}`} role="status">
          <span className="status-dot" aria-hidden="true" />{status}
        </span>
      </div>
      <main id="main" ref={mainRef} tabIndex={-1} className="app-main">
        <Outlet />
      </main>
      <footer className="app-footer">
        <p className="disclaimer">{t('home.disclaimer')}</p>
        <p style={{ marginTop: 6 }}>GovReach AI — graduation prototype</p>
      </footer>
    </div>
  )
}
