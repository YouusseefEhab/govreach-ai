import { t, useInterfaceLanguage } from './i18n'
import { Link, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Campaigns from './pages/Campaigns';
import CampaignForm from './components/CampaignForm';
import EditCampaign from './pages/EditCampaign';
import CampaignDetail from './pages/CampaignDetail';
import ContentEditor from './pages/ContentEditor';
export default function App() {
    useInterfaceLanguage();
    return (<Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />}/>
        <Route path="campaigns" element={<Campaigns />}/>
        <Route path="campaigns/new" element={<CampaignForm key="new"/>}/>
        <Route path="campaigns/:campaignId" element={<CampaignDetail />}/>
        <Route path="campaigns/:campaignId/edit" element={<EditCampaign />}/>
        <Route path="contents/:contentId" element={<ContentEditor />}/>
        <Route path="*" element={<section className="empty-state">
            <h1>{t("الصفحة مش موجودة")}</h1>
            <p>{t("ممكن يكون الرابط اتغيّر. ارجع للحملات عشان تكمّل.")}</p>
            <Link className="button" to="/campaigns">{t("ارجع للحملات")}</Link>
          </section>}/>
      </Route>
    </Routes>);
}
