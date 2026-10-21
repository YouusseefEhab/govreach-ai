import { Link, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Campaigns from './pages/Campaigns'
import CampaignForm from './components/CampaignForm'
import EditCampaign from './pages/EditCampaign'
import CampaignDetail from './pages/CampaignDetail'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="campaigns" element={<Campaigns />} />
        <Route path="campaigns/new" element={<CampaignForm key="new" />} />
        <Route path="campaigns/:campaignId" element={<CampaignDetail />} />
        <Route path="campaigns/:campaignId/edit" element={<EditCampaign />} />
        <Route path="*" element={
          <section className="empty-state">
            <h1>الصفحة مش موجودة</h1>
            <p>ممكن يكون الرابط اتغيّر. ارجع للحملات عشان تكمّل.</p>
            <Link className="button" to="/campaigns">ارجع للحملات</Link>
          </section>
        } />
      </Route>
    </Routes>
  )
}
