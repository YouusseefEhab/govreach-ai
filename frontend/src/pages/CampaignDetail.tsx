import { t, useInterfaceLanguage, getInterfaceLocale } from '../i18n'
import { useIsMutating, useQuery } from '@tanstack/react-query';
import { Link, useLocation, useParams } from 'react-router-dom';
import { campaignQuery } from '../queries';
import { ErrorNotice } from '../components/Feedback';
import { messages } from '../messages';
import DeleteCampaign from '../components/DeleteCampaign';
import GenerationWorkspace from '../components/GenerationWorkspace';
const languages: Record<string, string> = { arabic: messages.arabic, english: messages.english, both: messages.both };
export default function CampaignDetail() {
    useInterfaceLanguage();
    const { campaignId = '' } = useParams();
    const id = /^\d+$/.test(campaignId) ? Number(campaignId) : 0;
    const validId = Number.isSafeInteger(id) && id > 0;
    const query = useQuery(campaignQuery(id));
    const { state } = useLocation();
    const generating = useIsMutating({ mutationKey: ['generate-text', id] }) > 0;
    if (!validId)
        return <section className="panel"><h1>{t("رقم الحملة غير صحيح")}</h1><Link className="text-link" to="/campaigns">{t("ارجع للحملات")}</Link></section>;
    return (<section>
      <Link className="text-link" to="/campaigns">{t("← كل الحملات")}</Link>
      {query.isPending && <p role="status">{t("بنحمّل بيانات الحملة…")}</p>}
      {query.isError && <ErrorNotice error={query.error} retry={() => { void query.refetch(); }}/>}
      {query.isSuccess && <>
        {(state?.created || state?.updated) && <p className="notice success-notice" role="status">{state?.updated ? t('تم حفظ التعديلات بنجاح.') : t('تم حفظ الحملة بنجاح.')}</p>}
        <div className="page-heading"><p className="eyebrow">{t("تفاصيل الحملة · رقم ")}<bdi>{query.data.id}</bdi></p><h1 dir="auto">{query.data.title}</h1></div>
        <article className="panel campaign-detail">
          <h2>{t("هدف الحملة")}</h2>
          <p className="campaign-objective" dir="auto">{query.data.objective}</p>
          <dl className="campaign-metadata">
            <div><dt>{t("المجال")}</dt><dd><bdi>{query.data.domain === 'traffic_safety' ? t(messages.traffic_safety) : query.data.domain}</bdi></dd></div>
            <div><dt>{t("لغة المحتوى")}</dt><dd><bdi>{t(languages[query.data.language]) ?? query.data.language}</bdi></dd></div>
            <div><dt>{t("الحالة")}</dt><dd><span className="pill"><bdi>{query.data.status === 'draft' ? t(messages.draft) : query.data.status}</bdi></span></dd></div>
            <div><dt>{t("تاريخ الإنشاء")}</dt><dd><time dateTime={query.data.created_at}>{new Intl.DateTimeFormat(getInterfaceLocale(), { dateStyle: 'medium' }).format(new Date(query.data.created_at))}</time></dd></div>
          </dl>
        </article>
        {!generating && <div className="campaign-controls">
          <Link className="button" to={`/campaigns/${id}/edit`}>{t("تعديل الحملة")}</Link>
          <DeleteCampaign key={id} campaign={query.data}/>
        </div>}
        <GenerationWorkspace key={id} campaign={query.data}/>
      </>}
    </section>);
}
