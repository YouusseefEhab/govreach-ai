import { useState } from 'react'
import { useIsMutating, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getInterfaceLocale, t, useInterfaceLanguage } from '../i18n'
import { imageFileUrl, reviewImage } from '../services/images'
import type { StoredImage } from '../services/types'
import { imageStateLabel } from './image-labels'

const snapshotLabels = { headline: 'العنوان', slogan: 'الشعار', awareness_message: 'رسالة التوعية',
  social_caption: 'منشور التواصل الاجتماعي', call_to_action: 'الدعوة للفعل' }
function safeSourceUrl(value: unknown) {
  try { const url = new URL(typeof value === 'string' ? value : ''); return url.protocol === 'https:' ? url.href : undefined }
  catch { return undefined }
}

export default function ImageCard({ item }: { item: StoredImage }) {
  useInterfaceLanguage()
  const client = useQueryClient()
  const [preview, setPreview] = useState<'loading' | 'loaded' | 'error'>('loading')
  const [version, setVersion] = useState(0)
  const [checked, setChecked] = useState(false)
  const mutationKey = ['review-image', item.id]
  const busy = useIsMutating({ mutationKey }) > 0
  const review = useMutation({
    mutationKey, mutationFn: (status: StoredImage['review_status']) => reviewImage(item.id, status), retry: false,
    onSuccess: (saved) => {
      client.setQueryData(['image', saved.id], saved)
      void client.invalidateQueries({ queryKey: ['campaign-images', saved.campaign_id] })
      setChecked(false)
    },
    onError: () => { void client.invalidateQueries({ queryKey: ['campaign-images', item.campaign_id] }) },
  })
  const ready = item.request_state === 'ready'
  const url = imageFileUrl(item.id)
  const snapshot = item.source_snapshot.content && typeof item.source_snapshot.content === 'object'
    ? item.source_snapshot.content as Record<string, unknown> : {}
  const arabic = item.source_snapshot.language === 'arabic'
  return <article className="panel image-card" aria-label={`${t('صورة رقم ')}${item.id}`}>
    <div className="history-heading">
      <h3>{t('صورة رقم ')}{item.id}</h3>
      <span className="pill">{imageStateLabel(item.request_state)}</span>
    </div>
    <p>{t('حالة المراجعة: ')}{item.review_status === 'approved' ? t('معتمد') : item.review_status === 'rejected' ? t('مرفوض') : t('مسودة للمراجعة')}</p>
    {!item.source_is_current && <p className="notice error-notice" role="status">
      {t('النص الأصلي اتغير أو مش معتمد دلوقتي. الصورة دي محتاجة مراجعة ومينفعش تعتمدها على النص الحالي.')}
      {item.review_status === 'approved' && t(' الاعتماد الظاهر قرار سابق، مش اعتماد للنص الحالي.')}
    </p>}
    {item.provider === 'fake' && <p className="form-note">{t('دي صورة اختبار زرقا من المزوّد التجريبي، مش صورة حملة مولّدة بالذكاء الاصطناعي.')}</p>}
    {ready ? <>
      <figure>
        <img className="image-preview" src={version ? `${url}?preview=${version}` : url} loading="lazy"
          alt={`${t('صورة الحملة للمراجعة: ')}${item.visual_brief}`} onLoad={() => setPreview('loaded')} onError={() => setPreview('error')} />
        <figcaption>{t('راجع المشهد ومعدات السلامة والتفاصيل والكتابة غير المقصودة قبل الاعتماد.')}</figcaption>
      </figure>
      {preview === 'error' && <div className="notice error-notice" role="alert">
        <p>{t('معاينة الصورة مش متاحة. ممكن الملف ناقص أو فشل التحقق؛ متعتمدش الصورة قبل ما تظهر.')}</p>
        <button type="button" className="button secondary" onClick={() => { setPreview('loading'); setVersion((value) => value + 1) }}>{t('إعادة تحميل المعاينة')}</button>
      </div>}
      <div className="form-actions">
        <a className="button secondary" href={imageFileUrl(item.id, true)}>{t('تنزيل الصورة')}</a>
        <a className="text-link" href={url} target="_blank" rel="noreferrer">{t('افتح الصورة بالحجم الكامل')}</a>
      </div>
      <fieldset className="image-review" disabled={busy}>
        <legend>{t('مراجعة الصورة بشكل مستقل')}</legend>
        <label className="image-check"><input type="checkbox" checked={checked} disabled={preview !== 'loaded' || !item.source_is_current}
          onChange={(event) => setChecked(event.target.checked)} />{t('راجعت الصورة وتأكدت من وضوح الرسالة وصحة تفاصيل السلامة.')}</label>
        <div className="form-actions">
          <button type="button" className="button" disabled={!checked || preview !== 'loaded' || !item.source_is_current || item.review_status === 'approved'}
            onClick={() => review.mutate('approved')}>{t('اعتماد الصورة')}</button>
          <button type="button" className="button secondary" disabled={item.review_status === 'rejected'} onClick={() => review.mutate('rejected')}>{t('رفض الصورة')}</button>
          <button type="button" className="button secondary" disabled={item.review_status === 'draft'} onClick={() => review.mutate('draft')}>{t('إرجاع الصورة لمسودة')}</button>
        </div>
      </fieldset>
      {review.isError && <p className="notice error-notice" role="alert">{t(review.error.message)}</p>}
      {review.isSuccess && <p role="status">{t('اتحفظ قرار مراجعة الصورة. ده مش نشر للحملة.')}</p>}
    </> : <p className="form-note">{t('مفيش ملف جاهز للطلب ده. تحديث السجل مش بيبدأ توليد جديد.')}</p>}
    <details className="content-sources">
      <summary>{t('بيانات الصورة والنص المستخدم')}</summary>
      <p><Link className="text-link" to={`/contents/${item.source_content_id}`}>{t('راجع النص الأصلي رقم ')}{item.source_content_id}</Link></p>
      <p dir="auto">{item.visual_brief}</p>
      <dl className="generation-metadata">
        <dt>{t('المزوّد والموديل')}</dt><dd><bdi>{item.provider} · {item.model}</bdi></dd>
        <dt>{t('تاريخ الإنشاء')}</dt><dd>{new Intl.DateTimeFormat(getInterfaceLocale(), { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(item.created_at))}</dd>
        <dt>{t('الأبعاد')}</dt><dd>{item.width && item.height ? `${item.width} × ${item.height}` : '—'}</dd>
        <dt>{t('مفتاح الطلب')}</dt><dd><bdi>{item.idempotency_key}</bdi></dd>
        <dt>{t('نسخة تعليمات التوليد')}</dt><dd><bdi>{item.prompt_version}</bdi></dd>
        {item.failure_code && <><dt>{t('رمز المشكلة')}</dt><dd><bdi>{item.failure_code}</bdi></dd></>}
      </dl>
      <p>{t('النص المحفوظ وقت التوليد')}</p>
      <dl className="text-package image-snapshot">{Object.entries(snapshotLabels).map(([field, label]) => typeof snapshot[field] === 'string'
        ? <div key={field}><dt>{t(label)}</dt><dd dir={arabic ? 'rtl' : 'ltr'} lang={arabic ? 'ar-EG' : 'en'}>{snapshot[field]}</dd></div> : null)}</dl>
      <p>{t('المراجع المحفوظة مع الطلب، مش تدقيق تلقائي للصورة.')}</p>
      {item.source_references.length === 0 ? <p>{t('مفيش مصادر محفوظة مع النسخة دي.')}</p> : <ul>{item.source_references.map((reference, index) => {
        const href = safeSourceUrl(reference.url)
        const title = typeof reference.title === 'string' ? reference.title : t('مصدر')
        return <li key={index}>{href ? <a className="text-link" href={href} target="_blank" rel="noreferrer">{title}</a> : <bdi>{title}</bdi>}
          {typeof reference.publisher === 'string' && <span> · <bdi>{reference.publisher}</bdi></span>}</li>
      })}</ul>}
    </details>
  </article>
}
