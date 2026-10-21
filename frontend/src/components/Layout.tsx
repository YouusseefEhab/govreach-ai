import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { healthQuery } from '../queries'
import { messages } from '../messages'

export default function Layout() {
  const health = useQuery(healthQuery)
  const { pathname } = useLocation()
  const mainRef = useRef<HTMLElement>(null)
  const previousPath = useRef(pathname)

  useEffect(() => {
    if (previousPath.current !== pathname) {
      mainRef.current?.focus()
      previousPath.current = pathname
    }
    document.title = `${pathname.startsWith('/contents/') ? 'مراجعة المحتوى' : pathname.startsWith('/campaigns') ? messages.campaigns : messages.home} | GovReach AI`
  }, [pathname])

  const available = health.isSuccess && health.data.status === 'healthy'
  const status = health.isPending ? messages.checking
    : available ? messages.connected : messages.disconnected

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">{messages.skipLink}</a>
      <aside className="sidebar">
        <Link className="brand" to="/" aria-label="GovReach AI — الرئيسية">
          <span className="brand-icon" aria-hidden="true">G</span>
          <span><b dir="ltr">GovReach AI</b><small>{messages.tagline}</small></span>
        </Link>
        <nav aria-label={messages.navigation}>
          <NavLink to="/" end>{messages.home}</NavLink>
          <NavLink to="/campaigns">{messages.campaigns}</NavLink>
        </nav>
        <div className="sidebar-note">
          <span className="eyebrow">من الوعي للفعل</span>
          <p>رسالة واضحة، بلغة قريبة من الناس.</p>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>مساحة عمل الحملات</span>
          <span className={`connection ${available ? 'online' : ''}`} role="status">
            <span className="status-dot" aria-hidden="true" />{status}
          </span>
        </header>
        <main id="main" ref={mainRef} tabIndex={-1} className="main-content">
          <Outlet />
        </main>
        <footer>GovReach AI · مشروع تخرج · المحتوى بيحتاج مراجعة بشرية قبل الاستخدام</footer>
      </div>
    </div>
  )
}
