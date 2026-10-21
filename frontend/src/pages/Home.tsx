import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { healthQuery } from '../queries'
import { ErrorNotice } from '../components/Feedback'

export default function Home() {
  const health = useQuery(healthQuery)

  return (
    <>
      <section className="welcome-panel">
        <div className="welcome-copy">
          <p className="eyebrow">سلامة أكتر. وعي أقرب.</p>
          <h1>كل حملة بتبدأ<br />برسالة تفرق.</h1>
          <p className="description">حضّر مسودات توعية للسلامة المرورية بالعربي المصري والإنجليزي، وراجعها قبل ما تستخدمها.</p>
          <Link className="button" to="/campaigns">شوف حملاتك <span aria-hidden="true">←</span></Link>
        </div>
        <div className="journey-card">
          <span className="pill">رحلة الرسالة</span>
          <ol>
            <li><b>حدّد الهدف</b><span>رسالة مناسبة للجمهور اللي عايز توصله.</span></li>
            <li><b>حضّر المسودة</b><span>محتوى بالعربي المصري والإنجليزي.</span></li>
            <li><b>راجع واعتمد</b><span>راجع الصياغة والمعنى والمصادر لكل لغة.</span></li>
          </ol>
        </div>
      </section>
      <section className="home-details" aria-label="عن مساحة العمل">
        <article className="panel">
          <span className="eyebrow">مجالنا الأول</span>
          <h2>السلامة المرورية</h2>
          <p>من ربط حزام الأمان لتجنّب التشتت على الطريق، الوعي بيبدأ بكلام واضح وقريب من الناس.</p>
        </article>
        <article className="panel">
          <span className="eyebrow">المراجعة أولاً</span>
          <h2>المسودة بداية للمراجعة</h2>
          <p>المصادر بتساعد في إعداد المسودة. وجودها مش ضمان لصحة كل جملة، واعتماد المحتوى مش معناه نشره.</p>
        </article>
      </section>
      {health.isError && <ErrorNotice error={health.error} retry={() => { void health.refetch() }} />}
    </>
  )
}
