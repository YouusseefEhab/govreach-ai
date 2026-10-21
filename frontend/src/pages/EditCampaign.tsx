import { t, useInterfaceLanguage } from '../i18n'
import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { campaignQuery } from '../queries';
import CampaignForm from '../components/CampaignForm';
import { ErrorNotice } from '../components/Feedback';
export default function EditCampaign() {
    useInterfaceLanguage();
    const { campaignId = '' } = useParams();
    const id = /^\d+$/.test(campaignId) ? Number(campaignId) : 0;
    const valid = Number.isSafeInteger(id) && id > 0;
    const query = useQuery(campaignQuery(id));
    if (!valid)
        return <section className="panel"><h1>{t("رقم الحملة غير صحيح")}</h1><Link to="/campaigns">{t("ارجع للحملات")}</Link></section>;
    if (query.isPending)
        return <p role="status">{t("بنحمّل بيانات الحملة…")}</p>;
    if (query.isError)
        return <><Link className="text-link" to="/campaigns">{t("كل الحملات")}</Link><ErrorNotice error={query.error} retry={() => { void query.refetch(); }}/></>;
    return <CampaignForm key={id} campaign={query.data}/>;
}
