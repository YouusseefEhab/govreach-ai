import { t, useInterfaceLanguage, setInterfaceLanguage } from '../i18n'
import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { healthQuery } from '../queries';
import { messages } from '../messages';
export default function Layout() {
    const interfaceLanguage = useInterfaceLanguage();
    const health = useQuery(healthQuery);
    const { pathname } = useLocation();
    const mainRef = useRef<HTMLElement>(null);
    const previousPath = useRef(pathname);
    useEffect(() => {
        if (previousPath.current !== pathname) {
            mainRef.current?.focus();
            previousPath.current = pathname;
        }
        document.title = `${pathname.startsWith('/contents/') ? t('مراجعة المحتوى') : pathname.startsWith('/campaigns') ? t(messages.campaigns) : t(messages.home)} | GovReach AI`;
    }, [pathname, interfaceLanguage]);
    useEffect(() => {
        document.documentElement.lang = interfaceLanguage === 'ar' ? 'ar-EG' : 'en';
        document.documentElement.dir = interfaceLanguage === 'ar' ? 'rtl' : 'ltr';
    }, [interfaceLanguage]);
    const available = health.isSuccess && health.data.status === 'healthy';
    const status = health.isPending ? t(messages.checking) : available ? t(messages.connected) : t(messages.disconnected);
    return (<div className="app-shell">
      <a className="skip-link" href="#main">{t(messages.skipLink)}</a>
      <aside className="sidebar">
        <Link className="brand" to="/" aria-label={t("GovReach AI — الرئيسية")}>
          <span className="brand-icon" aria-hidden="true">G</span>
          <span><b dir="ltr">GovReach AI</b><small>{t(messages.tagline)}</small></span>
        </Link>
        <nav aria-label={t(messages.navigation)}>
          <NavLink to="/" end>{t(messages.home)}</NavLink>
          <NavLink to="/campaigns">{t(messages.campaigns)}</NavLink>
        </nav>
        <div className="sidebar-note">
          <span className="eyebrow">{t("من الوعي للفعل")}</span>
          <p>{t("رسالة واضحة، بلغة قريبة من الناس.")}</p>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>{t("مساحة عمل الحملات")}</span>
          <label className="language-switch" htmlFor="interface-language">
            <span>لغة الواجهة / Interface language</span>
            <select id="interface-language" value={interfaceLanguage} onChange={(event) => setInterfaceLanguage(event.target.value === 'en' ? 'en' : 'ar')}>
              <option value="ar">العربية</option><option value="en">English</option>
            </select>
          </label>
          <span className={`connection ${available ? 'online' : ''}`} role="status">
            <span className="status-dot" aria-hidden="true"/>{status}
          </span>
        </header>
        <main id="main" ref={mainRef} tabIndex={-1} className="main-content">
          <Outlet />
        </main>
        <footer>{t("GovReach AI · مشروع تخرج · المحتوى بيحتاج مراجعة بشرية قبل الاستخدام")}</footer>
      </div>
    </div>);
}
