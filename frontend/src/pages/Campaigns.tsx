import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { campaignsQuery } from '../queries'
import { messages } from '../messages'
import { ErrorNotice } from '../components/Feedback'

const PAGE_SIZE = 20
const languageLabels: Record<string, string> = {
  arabic: messages.arabic, english: messages.english, both: messages.both,
}
const dateFormatter = new Intl.DateTimeFormat('ar-EG', { dateStyle: 'medium' })

export default function Campaigns() {
  const [params, setParams] = useSearchParams()
  const rawPage = params.get('page') ?? '1'
  const parsedPage = /^\d+$/.test(rawPage) ? Number(rawPage) : 1
  const page = Number.isSafeInteger(parsedPage) && parsedPage > 0 && parsedPage <= 100_000
    ? parsedPage : 1
  const query = useQuery(campaignsQuery((page - 1) * PAGE_SIZE, PAGE_SIZE))

  const changePage = (next: number) => {
    setParams(next === 1 ? {} : { page: String(next) })
    document.getElementById('campaign-heading')?.focus()
  }

  return (
    <section aria-labelledby="campaign-heading">
      <div className="page-heading">
        <p className="eyebrow">رسائلك في مكان واحد</p>
        <h1 id="campaign-heading" tabIndex={-1}>{messages.campaigns}</h1>
        <p>استعرض الحملات المحفوظة ولغات محتواها.</p>
        <Link className="button" to="/campaigns/new">+ حملة جديدة</Link>
      </div>
      {query.isPending && <div className="panel" role="status">{messages.loading}</div>}
      {query.isError && <ErrorNotice error={query.error} retry={() => { void query.refetch() }} />}
      {query.isSuccess && (
        <>
          {query.data.length === 0 ? (
            <div className="panel empty-state">
              <h2>{page === 1 ? 'لسه مفيش حملات محفوظة' : 'مفيش حملات تانية في الصفحة دي'}</h2>
              <p>{page === 1 ? 'الحملات المحفوظة هتظهر هنا.' : 'ارجع للصفحة اللي قبلها عشان تشوف حملاتك.'}</p>
            </div>
          ) : (
            <div className="table-scroll panel">
              <table>
                <caption className="visually-hidden">الحملات المحفوظة، صفحة {page}</caption>
                <thead><tr>
                  <th scope="col">{messages.campaignTitle}</th>
                  <th scope="col">{messages.domain}</th>
                  <th scope="col">{messages.language}</th>
                  <th scope="col">{messages.status}</th>
                  <th scope="col">{messages.date}</th>
                </tr></thead>
                <tbody>{query.data.map((campaign) => (
                  <tr key={campaign.id}>
                    <th scope="row"><Link className="text-link" to={`/campaigns/${campaign.id}`}><bdi>{campaign.title}</bdi></Link><small className="record-id">رقم <bdi>{campaign.id}</bdi></small></th>
                    <td><bdi>{campaign.domain === 'traffic_safety' ? messages.traffic_safety : campaign.domain}</bdi></td>
                    <td><bdi>{languageLabels[campaign.language] ?? campaign.language}</bdi></td>
                    <td><span className="pill"><bdi>{campaign.status === 'draft' ? messages.draft : campaign.status}</bdi></span></td>
                    <td><time dateTime={campaign.created_at}>{dateFormatter.format(new Date(campaign.created_at))}</time></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
          <nav className="pagination" aria-label="صفحات الحملات">
            <button className="button secondary" disabled={page === 1} onClick={() => changePage(page - 1)}>{messages.previous}</button>
            <span aria-live="polite">صفحة {page.toLocaleString('ar-EG')}</span>
            <button className="button secondary" disabled={query.data.length < PAGE_SIZE || page >= 100_000} onClick={() => changePage(page + 1)}>{messages.next}</button>
          </nav>
        </>
      )}
    </section>
  )
}
