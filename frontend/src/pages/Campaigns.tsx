import { t, useInterfaceLanguage, getInterfaceLocale } from '../i18n'
import { useQuery } from '@tanstack/react-query';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { campaignsQuery } from '../queries';
import { messages } from '../messages';
import { ErrorNotice } from '../components/Feedback';
const PAGE_SIZE = 20;
const languageLabels: Record<string, string> = {
    arabic: messages.arabic, english: messages.english, both: messages.both,
};
export default function Campaigns() {
    useInterfaceLanguage();
    const dateFormatter = new Intl.DateTimeFormat(getInterfaceLocale(), { dateStyle: 'medium' });
    const { state } = useLocation();
    const [params, setParams] = useSearchParams();
    const rawPage = params.get('page') ?? '1';
    const parsedPage = /^\d+$/.test(rawPage) ? Number(rawPage) : 1;
    const page = Number.isSafeInteger(parsedPage) && parsedPage > 0 && parsedPage <= 100000
        ? parsedPage : 1;
    const query = useQuery(campaignsQuery((page - 1) * PAGE_SIZE, PAGE_SIZE));
    const changePage = (next: number) => {
        setParams(next === 1 ? {} : { page: String(next) });
        document.getElementById('campaign-heading')?.focus();
    };
    return (<section aria-labelledby="campaign-heading">
      {state?.deleted && <p className="notice success-notice" role="status">{t("تم حذف الحملة ومحتواها.")}</p>}
      <div className="page-heading">
        <p className="eyebrow">{t("رسائلك في مكان واحد")}</p>
        <h1 id="campaign-heading" tabIndex={-1}>{t(messages.campaigns)}</h1>
        <p>{t("استعرض الحملات المحفوظة ولغات محتواها.")}</p>
        <Link className="button" to="/campaigns/new">{t("+ حملة جديدة")}</Link>
      </div>
      {query.isPending && <div className="panel" role="status">{t(messages.loading)}</div>}
      {query.isError && <ErrorNotice error={query.error} retry={() => { void query.refetch(); }}/>}
      {query.isSuccess && (<>
          {query.data.length === 0 ? (<div className="panel empty-state">
              <h2>{page === 1 ? t('لسه مفيش حملات محفوظة') : t('مفيش حملات تانية في الصفحة دي')}</h2>
              <p>{page === 1 ? t('الحملات المحفوظة هتظهر هنا.') : t('ارجع للصفحة اللي قبلها عشان تشوف حملاتك.')}</p>
            </div>) : (<div className="table-scroll panel" tabIndex={0} role="region" aria-label={t(messages.campaigns)}>
              <table>
                <caption className="visually-hidden">{t("الحملات المحفوظة، صفحة ")}{page}</caption>
                <thead><tr>
                  <th scope="col">{t(messages.campaignTitle)}</th>
                  <th scope="col">{t(messages.domain)}</th>
                  <th scope="col">{t(messages.language)}</th>
                  <th scope="col">{t(messages.status)}</th>
                  <th scope="col">{t(messages.date)}</th>
                </tr></thead>
                <tbody>{query.data.map((campaign) => (<tr key={campaign.id}>
                    <th scope="row"><Link className="text-link" to={`/campaigns/${campaign.id}`}><bdi>{campaign.title}</bdi></Link><small className="record-id">{t("رقم ")}<bdi>{campaign.id}</bdi></small></th>
                    <td><bdi>{campaign.domain === 'traffic_safety' ? t(messages.traffic_safety) : campaign.domain}</bdi></td>
                    <td><bdi>{t(languageLabels[campaign.language]) ?? campaign.language}</bdi></td>
                    <td><span className="pill"><bdi>{campaign.status === 'draft' ? t(messages.draft) : campaign.status}</bdi></span></td>
                    <td><time dateTime={campaign.created_at}>{dateFormatter.format(new Date(campaign.created_at))}</time></td>
                  </tr>))}</tbody>
              </table>
            </div>)}
          <nav className="pagination" aria-label={t("صفحات الحملات")}>
            <button className="button secondary" disabled={page === 1} onClick={() => changePage(page - 1)}>{t(messages.previous)}</button>
            <span aria-live="polite">{t("صفحة ")}{page.toLocaleString(getInterfaceLocale())}</span>
            <button className="button secondary" disabled={query.data.length < PAGE_SIZE || page >= 100000} onClick={() => changePage(page + 1)}>{t(messages.next)}</button>
          </nav>
        </>)}
    </section>);
}
