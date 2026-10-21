import { t, useInterfaceLanguage } from '../i18n'
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { healthQuery } from '../queries';
import { ErrorNotice } from '../components/Feedback';
export default function Home() {
    useInterfaceLanguage();
    const health = useQuery(healthQuery);
    return (<>
      <section className="welcome-panel">
        <div className="welcome-copy">
          <p className="eyebrow">{t("سلامة أكتر. وعي أقرب.")}</p>
          <h1>{t("كل حملة بتبدأ")}<br />{t("برسالة تفرق.")}</h1>
          <p className="description">{t("حضّر مسودات توعية للسلامة المرورية بالعربي المصري والإنجليزي، وراجعها قبل ما تستخدمها.")}</p>
          <Link className="button" to="/campaigns">{t("شوف حملاتك ")}<span className="direction-arrow" aria-hidden="true">←</span></Link>
        </div>
        <div className="journey-card">
          <span className="pill">{t("رحلة الرسالة")}</span>
          <ol>
            <li><b>{t("حدّد الهدف")}</b><span>{t("رسالة مناسبة للجمهور اللي عايز توصله.")}</span></li>
            <li><b>{t("حضّر المسودة")}</b><span>{t("محتوى بالعربي المصري والإنجليزي.")}</span></li>
            <li><b>{t("راجع واعتمد")}</b><span>{t("راجع الصياغة والمعنى والمصادر لكل لغة.")}</span></li>
          </ol>
        </div>
      </section>
      <section className="home-details" aria-label={t("عن مساحة العمل")}>
        <article className="panel">
          <span className="eyebrow">{t("مجالنا الأول")}</span>
          <h2>{t("السلامة المرورية")}</h2>
          <p>{t("من ربط حزام الأمان لتجنّب التشتت على الطريق، الوعي بيبدأ بكلام واضح وقريب من الناس.")}</p>
        </article>
        <article className="panel">
          <span className="eyebrow">{t("المراجعة أولاً")}</span>
          <h2>{t("المسودة بداية للمراجعة")}</h2>
          <p>{t("المصادر بتساعد في إعداد المسودة. وجودها مش ضمان لصحة كل جملة، واعتماد المحتوى مش معناه نشره.")}</p>
        </article>
      </section>
      {health.isError && <ErrorNotice error={health.error} retry={() => { void health.refetch(); }}/>}
    </>);
}
