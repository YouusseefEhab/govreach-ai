import { t, useInterfaceLanguage, getInterfaceLocale } from '../i18n'
import type { StoredContent, TextPackage } from '../services/types';
import { Link } from 'react-router-dom';
import CopyButton from './CopyButton';
import { packageText } from '../services/clipboard';
const fieldLabels: Record<keyof TextPackage, string> = {
    headline: 'العنوان', slogan: 'الشعار', awareness_message: 'رسالة التوعية',
    social_caption: 'منشور التواصل الاجتماعي', call_to_action: 'الدعوة للفعل',
};
const statuses = { draft: 'مسودة للمراجعة', approved: 'معتمد', rejected: 'مرفوض' };
function sourceUrl(value: unknown): string | undefined {
    if (typeof value !== 'string')
        return undefined;
    try {
        const url = new URL(value);
        return url.protocol === 'https:' ? url.href : undefined;
    }
    catch {
        return undefined;
    }
}
export default function ContentCard({ item, showEditorLink = true }: {
    item: StoredContent;
    showEditorLink?: boolean;
}) {
    useInterfaceLanguage();
    return (<article className="panel content-card" aria-label={`${item.language === 'arabic' ? t('المحتوى العربي') : 'English content'} — ${item.id}`}>
      <div className="content-card-heading">
        <h3>{item.language === 'arabic' ? t('عربي مصري') : 'English'}</h3>
        <span className="pill">{t(statuses[item.review_status])}</span>
        <CopyButton text={packageText(item.content)} label="نسخ النص كله" />
      </div>
      <dl className="text-package">
        {(Object.keys(fieldLabels) as (keyof TextPackage)[]).map((field) => (<div key={field}><dt className="text-field-heading">{t(fieldLabels[field])}<CopyButton text={item.content[field]} label={`${t('نسخ')} ${t(fieldLabels[field])}`} /></dt><dd lang={item.language === 'arabic' ? 'ar-EG' : 'en'} dir={item.language === 'arabic' ? 'rtl' : 'ltr'}>{item.content[field]}</dd></div>))}
      </dl>
      <details className="content-sources">
        <summary>{t("المصادر وتفاصيل التوليد")}</summary>
        <p>{t("المصادر دي اتقدمت أثناء التوليد؛ مش تدقيق تلقائي لكل جملة أو اعتماد حكومي. راجع الصياغة والحقائق قبل الاستخدام.")}</p>
        {item.source_references.length === 0 ? <p>{t("مفيش مصادر محفوظة مع النسخة دي.")}</p> : <ul>{item.source_references.map((source, index) => {
                const url = sourceUrl(source.url);
                const title = typeof source.title === 'string' ? source.title : t('مصدر');
                return <li key={index}>{url ? <a className="text-link" href={url} target="_blank" rel="noopener noreferrer"><bdi>{title}</bdi></a> : <bdi>{title}</bdi>}
            {typeof source.publisher === 'string' && <span> — <bdi>{source.publisher}</bdi></span>}
            {typeof source.section === 'string' && <p><bdi>{source.section}</bdi></p>}
          </li>;
            })}</ul>}
        <dl className="generation-metadata">
          <div><dt>{t("رقم المحتوى")}</dt><dd>{item.id}</dd></div>
          <div><dt>{t("مجموعة التوليد")}</dt><dd><bdi>{item.generation_id}</bdi></dd></div>
          <div><dt>{t("التاريخ")}</dt><dd><time dateTime={item.created_at}>{new Intl.DateTimeFormat(getInterfaceLocale(), { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(item.created_at))}</time></dd></div>
          <div><dt>{t("المزوّد / النموذج")}</dt><dd><bdi>{item.provider} / {item.model}</bdi></dd></div>
          <div><dt>{t("نسخة التعليمات")}</dt><dd><bdi>{item.prompt_version}</bdi></dd></div>
        </dl>
      </details>
      {showEditorLink && <Link className="button secondary content-edit-link" to={`/contents/${item.id}`}>{t("تعديل ومراجعة النسخة")}</Link>}
    </article>);
}
